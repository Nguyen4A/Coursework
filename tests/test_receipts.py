from email.message import EmailMessage
import tempfile
from unittest.mock import MagicMock, patch

from django.contrib.auth.models import User
from django.test import TestCase
from django.urls import reverse

from knowledge.models import ShelfLifeRule
from pantry.models import Product
from receipts.models import EmailImportSource, ProcessingLog, ProductKeyword, ReceiptItem
from receipts.services import EmailImportService, OCRService, ReceiptImportService, ReceiptParser


class ReceiptTests(TestCase):
    def setUp(self):
        self.user = User.objects.create_user("u", password="p")

    def test_receipt_parser_filters_non_food(self):
        items = ReceiptParser().parse("Молоко 1 л 99.00\nПакет 1 шт 7.00\nХлеб 1 шт 50.00")
        names = [item.name.lower() for item in items]
        self.assertIn("молоко", names)
        self.assertIn("хлеб", names)
        self.assertNotIn("пакет", names)

    def test_receipt_parser_accepts_ocr_food_words(self):
        items = ReceiptParser().parse("1. Коктейль смесь сухофруктов и ядер орехов\nМаркет Перекрёсток, 150г\n279.99 * 1 шт. = 279.99")

        self.assertEqual(len(items), 1)
        self.assertEqual(items[0].name, "Коктейль смесь сухофруктов и ядер орехов")

    def test_import_text_creates_products(self):
        ReceiptImportService(self.user).import_text("Молоко 1 л 99.00\nПакет 1 шт 7.00")
        self.assertTrue(Product.objects.filter(user=self.user, name__icontains="Молоко").exists())
        self.assertFalse(Product.objects.filter(user=self.user, name__icontains="Пакет").exists())

    def test_import_text_removes_nul_bytes(self):
        receipt = ReceiptImportService(self.user).import_text("Хлеб\x00 1 шт 55.00")

        self.assertNotIn("\x00", receipt.original_text)
        self.assertTrue(Product.objects.filter(user=self.user, name__icontains="Хлеб").exists())

    def test_import_text_keeps_unknown_items_for_review(self):
        receipt = ReceiptImportService(self.user).import_text("Матча латте 1 шт 150.00")

        self.assertEqual(receipt.status, "needs_review")
        item = receipt.items.get()
        self.assertFalse(item.is_food)
        self.assertEqual(item.category, "не определено")
        self.assertEqual(item.review_status, ReceiptItem.REVIEW_PENDING)
        self.assertFalse(Product.objects.filter(user=self.user, name__icontains="Матча").exists())

    def test_review_unknown_item_as_food_learns_keyword(self):
        self.client.force_login(self.user)
        receipt = ReceiptImportService(self.user).import_text("Матча латте 1 шт 150.00")
        item = ReceiptItem.objects.get(receipt=receipt)

        response = self.client.post(
            reverse("receipts:item_review", args=[item.pk]),
            {"action": "food", "keyword": "матча", "category": "напитки", "shelf_life_days": "4"},
        )

        self.assertRedirects(response, reverse("receipts:detail", args=[receipt.pk]))
        item.refresh_from_db()
        receipt.refresh_from_db()
        self.assertTrue(item.is_food)
        self.assertEqual(item.category, "напитки")
        self.assertEqual(item.review_status, ReceiptItem.REVIEW_PROCESSED)
        self.assertEqual(receipt.status, "processed")
        product = Product.objects.get(user=self.user, name__icontains="Матча")
        self.assertEqual(product.shelf_life_days, 4)
        self.assertTrue(ProductKeyword.objects.filter(owner=self.user, word="матча", category="напитки", is_food=True).exists())
        self.assertTrue(ShelfLifeRule.objects.filter(owner=self.user, product_name="матча", shelf_life_days=4).exists())

    def test_review_unknown_item_as_non_food_learns_exclusion(self):
        self.client.force_login(self.user)
        receipt = ReceiptImportService(self.user).import_text("Стикеры кухонные 1 шт 150.00")
        item = ReceiptItem.objects.get(receipt=receipt)

        response = self.client.post(
            reverse("receipts:item_review", args=[item.pk]),
            {"action": "non_food", "keyword": "стикеры"},
        )

        self.assertRedirects(response, reverse("receipts:detail", args=[receipt.pk]))
        item.refresh_from_db()
        receipt.refresh_from_db()
        self.assertFalse(item.is_food)
        self.assertEqual(item.review_status, ReceiptItem.REVIEW_PROCESSED)
        self.assertEqual(receipt.status, "processed")
        self.assertTrue(ProductKeyword.objects.filter(owner=self.user, word="стикеры", is_food=False).exists())

    def test_ocr_service_does_not_send_files_to_external_api(self):
        with tempfile.NamedTemporaryFile(suffix=".png") as uploaded:
            uploaded.write(b"png bytes")
            uploaded.flush()

            text = OCRService().extract_text(uploaded.name)

        self.assertEqual(text, "")

    def test_ocr_service_returns_empty_text_for_local_noop(self):
        with tempfile.NamedTemporaryFile(suffix=".png") as uploaded:
            uploaded.write(b"png bytes")
            uploaded.flush()

            text = OCRService().extract_text(uploaded.name)

        self.assertEqual(text, "")

    @patch("receipts.services.imaplib.IMAP4_SSL")
    def test_email_import_skips_duplicate_uid(self, imap_cls):
        source = EmailImportSource.objects.create(user=self.user, host="imap.example.com", username="u", password="p")
        ProcessingLog.objects.create(user=self.user, source_type="email", external_id="1", status="success")
        connection = MagicMock()
        connection.list.return_value = ("OK", [b'(\\HasNoChildren) "/" "INBOX"'])
        connection.select.return_value = ("OK", [b""])
        connection.search.return_value = ("OK", [b"1"])
        imap_cls.return_value = connection
        count = EmailImportService(source).run()
        self.assertEqual(count, 0)
        connection.fetch.assert_not_called()

    def test_email_source_delete_removes_current_user_source(self):
        self.client.force_login(self.user)
        source = EmailImportSource.objects.create(user=self.user, host="imap.example.com", username="u", password="p")

        response = self.client.post(reverse("receipts:email_source_delete", args=[source.pk]))

        self.assertRedirects(response, reverse("receipts:email_sources"))
        self.assertFalse(EmailImportSource.objects.filter(pk=source.pk).exists())

    def test_email_source_update_changes_current_user_source(self):
        self.client.force_login(self.user)
        source = EmailImportSource.objects.create(user=self.user, host="imap.example.com", username="u", password="p")

        response = self.client.post(
            reverse("receipts:email_source_update", args=[source.pk]),
            {
                "name": "Новая почта",
                "host": "imap.mail.ru",
                "port": 993,
                "username": "user@mail.ru",
                "password": "app-password",
                "use_ssl": "on",
                "sender_filter": "чек",
                "is_active": "on",
            },
        )

        self.assertRedirects(response, reverse("receipts:email_sources"))
        source.refresh_from_db()
        self.assertEqual(source.name, "Новая почта")
        self.assertEqual(source.host, "imap.mail.ru")
        self.assertEqual(source.username, "user@mail.ru")
        self.assertEqual(source.sender_filter, "чек")

    @patch("receipts.services.imaplib.IMAP4_SSL")
    def test_email_import_supports_cyrillic_sender_filter(self, imap_cls):
        source = EmailImportSource.objects.create(
            user=self.user,
            host="imap.example.com",
            username="u",
            password="p",
            sender_filter="Золотое яблоко",
        )
        message = EmailMessage()
        message["From"] = "noreply@example.com"
        message["Subject"] = "Ваш чек"
        message.set_content("Золотое яблоко\nМолоко 1 л 99.00")
        connection = MagicMock()
        connection.list.return_value = ("OK", [b'(\\HasNoChildren) "/" "INBOX"'])
        connection.select.return_value = ("OK", [b""])
        connection.search.return_value = ("OK", [b"1"])
        connection.fetch.return_value = ("OK", [(b"1", message.as_bytes())])
        imap_cls.return_value = connection

        count = EmailImportService(source).run()

        self.assertEqual(count, 1)
        self.assertTrue(Product.objects.filter(user=self.user, name__icontains="Молоко").exists())

    @patch("receipts.services.imaplib.IMAP4_SSL")
    def test_email_import_checks_custom_mailboxes(self, imap_cls):
        source = EmailImportSource.objects.create(
            user=self.user,
            host="imap.example.com",
            username="u",
            password="p",
            sender_filter="Продукты",
        )
        message = EmailMessage()
        message["From"] = "sender@example.com"
        message["Subject"] = "Продукты"
        message.set_content("Хлеб 1 шт 55.00\nМасло 2 шт 180.00")
        connection = MagicMock()
        connection.list.return_value = ("OK", [b'(\\HasNoChildren) "/" "INBOX"', b'(\\HasNoChildren) "/" "Receipts"'])
        connection.select.return_value = ("OK", [b""])
        connection.search.side_effect = [("OK", [b""]), ("OK", [b"1"])]
        connection.fetch.return_value = ("OK", [(b"1", message.as_bytes())])
        imap_cls.return_value = connection

        count = EmailImportService(source).run()

        self.assertEqual(count, 1)
        self.assertTrue(Product.objects.filter(user=self.user, name__icontains="Хлеб").exists())
        self.assertTrue(Product.objects.filter(user=self.user, name__icontains="Масло").exists())
