import email
import imaplib
import json
import mimetypes
import re
from dataclasses import dataclass
from decimal import Decimal
from email.header import decode_header, make_header
from email.message import Message
from pathlib import Path
from urllib import request as urlrequest

from django.conf import settings
from django.db import IntegrityError, OperationalError, ProgrammingError
from django.db.models import Q
from django.utils import timezone

from knowledge.services import ShelfLifeService
from pantry.models import Product, ProductCategory

from .models import ProcessingLog, ProductKeyword, Receipt, ReceiptItem


@dataclass
class ParsedItem:
    name: str
    quantity: Decimal = Decimal("1")
    unit: str = "pcs"
    is_food: bool = True
    category: str = ""
    needs_review: bool = False


class FoodClassifier:
    UNKNOWN_CATEGORY = "не определено"
    NON_FOOD_CATEGORY = "не пищевое"
    FALLBACK_FOOD_WORDS = {
        "молоко": "молочные продукты",
        "кефир": "молочные продукты",
        "сыр": "молочные продукты",
        "йогурт": "молочные продукты",
        "творог": "молочные продукты",
        "сметана": "молочные продукты",
        "сливки": "молочные продукты",
        "ряженка": "молочные продукты",
        "айран": "молочные продукты",
        "хлеб": "хлеб",
        "батон": "хлеб",
        "курица": "мясо",
        "говядина": "мясо",
        "свинина": "мясо",
        "индейка": "мясо",
        "фарш": "мясо",
        "колбаса": "мясо",
        "сосиска": "мясо",
        "рыба": "рыба",
        "лосось": "рыба",
        "тунец": "рыба",
        "креветка": "рыба",
        "яйцо": "яйца",
        "яблоко": "фрукты",
        "банан": "фрукты",
        "апельсин": "фрукты",
        "груша": "фрукты",
        "виноград": "фрукты",
        "лимон": "фрукты",
        "картофель": "овощи",
        "томат": "овощи",
        "помидор": "овощи",
        "огурец": "овощи",
        "морковь": "овощи",
        "лук": "овощи",
        "капуста": "овощи",
        "перец": "овощи",
        "свекла": "овощи",
        "рис": "крупы",
        "гречка": "крупы",
        "овсянка": "крупы",
        "пшено": "крупы",
        "макароны": "бакалея",
        "масло": "бакалея",
        "орех": "бакалея",
        "сухофрукт": "бакалея",
        "коктейль": "бакалея",
        "мука": "бакалея",
        "сахар": "бакалея",
        "соль": "бакалея",
        "чай": "бакалея",
        "кофе": "бакалея",
        "сок": "напитки",
        "вода": "напитки",
        "морс": "напитки",
        "компот": "напитки",
    }
    FALLBACK_NON_FOOD_WORDS = {
        "пакет",
        "салфетки",
        "шампунь",
        "мыло",
        "гель",
        "зубная",
        "порошок",
        "батарейка",
        "лампа",
        "бумага",
        "крем",
        "дезодорант",
    }

    def __init__(self, user=None):
        self.user = user
        self._keywords = None

    def classify(self, name: str) -> tuple[bool, str]:
        lowered = self.normalize(name)
        keywords = self._load_keywords()
        if any(keyword.word in lowered for keyword in keywords if not keyword.is_food):
            return False, self.NON_FOOD_CATEGORY
        for keyword in keywords:
            if keyword.is_food and keyword.word in lowered:
                return True, keyword.category
        return False, self.UNKNOWN_CATEGORY

    @classmethod
    def normalize(cls, value: str) -> str:
        return re.sub(r"\s+", " ", value.strip().lower().replace("ё", "е"))

    @classmethod
    def learn(cls, user, word: str, category: str = "", is_food: bool = True) -> ProductKeyword:
        keyword, _ = ProductKeyword.objects.update_or_create(
            owner=user,
            word=cls.normalize(word),
            defaults={"category": category.strip(), "is_food": is_food, "source": ProductKeyword.SOURCE_USER},
        )
        return keyword

    def _load_keywords(self) -> list[ProductKeyword]:
        if self._keywords is not None:
            return self._keywords
        try:
            query = Q(owner__isnull=True)
            if self.user and getattr(self.user, "is_authenticated", False):
                query |= Q(owner=self.user)
            keywords = list(ProductKeyword.objects.filter(query))
        except (OperationalError, ProgrammingError):
            keywords = []
        if not keywords:
            keywords = self._fallback_keywords()
        self._keywords = sorted(keywords, key=lambda item: (item.owner_id is not None, len(item.word)), reverse=True)
        return self._keywords

    def _fallback_keywords(self) -> list[ProductKeyword]:
        keywords = [
            ProductKeyword(word=word, category=category, is_food=True, source=ProductKeyword.SOURCE_SYSTEM)
            for word, category in self.FALLBACK_FOOD_WORDS.items()
        ]
        keywords.extend(
            ProductKeyword(word=word, category=self.NON_FOOD_CATEGORY, is_food=False, source=ProductKeyword.SOURCE_SYSTEM)
            for word in self.FALLBACK_NON_FOOD_WORDS
        )
        return keywords


class ReceiptParser:
    LINE_RE = re.compile(r"^(?P<name>[A-Za-zА-Яа-яЁё0-9% .,'\-]+?)(?:\s+(?P<qty>\d+(?:[,.]\d+)?)\s*(?P<unit>кг|kg|г|g|л|l|шт|pcs|упак)?)?(?:\s+\d+[,.]\d{2})?$")

    def __init__(self, classifier=None):
        self.classifier = classifier or FoodClassifier()

    def parse(self, text: str, include_unknown: bool = False) -> list[ParsedItem]:
        items = []
        for raw_line in text.splitlines():
            line = raw_line.strip(" -\t")
            if not line or len(line) < 3:
                continue
            if self._is_noise(line):
                continue
            match = self.LINE_RE.match(line)
            if not match:
                continue
            name = self._clean_name(match.group("name"))
            if not name or len(name) < 3:
                continue
            is_food, category = self.classifier.classify(name)
            if not is_food and category != FoodClassifier.UNKNOWN_CATEGORY:
                continue
            if not is_food and not include_unknown:
                continue
            qty = Decimal((match.group("qty") or "1").replace(",", "."))
            unit = self._normalize_unit(match.group("unit") or "pcs")
            items.append(ParsedItem(name=name, quantity=qty, unit=unit, is_food=is_food, category=category, needs_review=not is_food))
        return items

    def _is_noise(self, line: str) -> bool:
        lowered = FoodClassifier.normalize(line)
        return any(token in lowered for token in ["итого", "кассир", "инн", "фн", "чек", "скидка", "налог", "оплата", "карта"])

    def _clean_name(self, value: str) -> str:
        value = re.sub(r"^\d+[.)]\s*", "", value)
        return re.sub(r"\s+", " ", value).strip(" .,-")

    def _normalize_unit(self, unit: str) -> str:
        unit = unit.lower()
        return {"шт": "pcs", "упак": "pack", "кг": "kg", "г": "g", "л": "l"}.get(unit, unit)


class OCRService:
    def extract_text(self, file_path: str) -> str:
        if not settings.OCR_API_URL or not settings.OCR_API_KEY:
            return ""
        body, content_type = self._build_request_body(file_path)
        req = urlrequest.Request(
            settings.OCR_API_URL,
            data=body,
            headers={"Content-Type": content_type},
            method="POST",
        )
        try:
            with urlrequest.urlopen(req, timeout=20) as response:
                payload = json.loads(response.read().decode("utf-8"))
        except (OSError, ValueError):
            return ""
        return self._parse_response(payload)

    def _build_request_body(self, file_path: str) -> tuple[bytes, str]:
        boundary = "----SmartFridgeOCRBoundary"
        path = Path(file_path)
        content_type = mimetypes.guess_type(path.name)[0] or "application/octet-stream"
        with path.open("rb") as uploaded:
            file_bytes = uploaded.read()

        fields = {
            "apikey": settings.OCR_API_KEY,
            "language": "rus",
            "isOverlayRequired": "false",
            "OCREngine": "2",
        }
        chunks = []
        for name, value in fields.items():
            chunks.extend(
                [
                    f"--{boundary}\r\n".encode("ascii"),
                    f'Content-Disposition: form-data; name="{name}"\r\n\r\n'.encode("ascii"),
                    str(value).encode("utf-8"),
                    b"\r\n",
                ]
            )
        chunks.extend(
            [
                f"--{boundary}\r\n".encode("ascii"),
                f'Content-Disposition: form-data; name="file"; filename="{path.name}"\r\n'.encode("utf-8"),
                f"Content-Type: {content_type}\r\n\r\n".encode("ascii"),
                file_bytes,
                b"\r\n",
                f"--{boundary}--\r\n".encode("ascii"),
            ]
        )
        return b"".join(chunks), f"multipart/form-data; boundary={boundary}"

    def _parse_response(self, payload: dict) -> str:
        if payload.get("IsErroredOnProcessing"):
            return ""
        results = payload.get("ParsedResults") or []
        texts = [result.get("ParsedText", "") for result in results if isinstance(result, dict)]
        return "\n".join(text.strip() for text in texts if text and text.strip())


class ReceiptImportService:
    def __init__(self, user):
        self.user = user
        self.classifier = FoodClassifier(user)
        self.parser = ReceiptParser(self.classifier)
        self.shelf_life = ShelfLifeService(user)

    def import_text(self, text: str, source: str = Receipt.SOURCE_TEXT, receipt: Receipt | None = None) -> Receipt:
        text = self._clean_text(text)
        receipt = receipt or Receipt.objects.create(user=self.user, source=source, original_text=text, status="processed")
        receipt.original_text = text
        receipt.status = "processed"
        receipt.save()
        needs_review = False
        for parsed in self.parser.parse(text, include_unknown=True):
            item = ReceiptItem.objects.create(
                receipt=receipt,
                raw_name=parsed.name,
                normalized_name=FoodClassifier.normalize(parsed.name),
                quantity=parsed.quantity,
                unit=parsed.unit,
                is_food=parsed.is_food,
                category=parsed.category,
            )
            if parsed.is_food:
                product = self._create_product(parsed, parsed.category, source)
                item.created_product = product
                item.save(update_fields=["created_product"])
            elif parsed.needs_review:
                needs_review = True
        if needs_review:
            receipt.status = "needs_review"
            receipt.save(update_fields=["status"])
        return receipt

    def confirm_item_as_food(self, item: ReceiptItem, category_name: str, keyword: str) -> ReceiptItem:
        category_name = category_name.strip() or "Продукты"
        keyword = keyword.strip() or item.normalized_name
        FoodClassifier.learn(self.user, keyword, category_name, is_food=True)
        item.is_food = True
        item.category = category_name
        if not item.created_product:
            parsed = ParsedItem(name=item.raw_name, quantity=item.quantity, unit=item.unit, is_food=True, category=category_name)
            item.created_product = self._create_product(parsed, category_name, item.receipt.source)
        item.save(update_fields=["is_food", "category", "created_product"])
        self._refresh_receipt_status(item.receipt)
        return item

    def confirm_item_as_non_food(self, item: ReceiptItem, keyword: str = "") -> ReceiptItem:
        FoodClassifier.learn(self.user, keyword.strip() or item.normalized_name, FoodClassifier.NON_FOOD_CATEGORY, is_food=False)
        item.is_food = False
        item.category = FoodClassifier.NON_FOOD_CATEGORY
        item.save(update_fields=["is_food", "category"])
        self._refresh_receipt_status(item.receipt)
        return item

    def _create_product(self, parsed: ParsedItem, category_name: str, source: str) -> Product:
        category, _ = ProductCategory.objects.get_or_create(name=category_name or "Продукты")
        product = Product(
            user=self.user,
            name=parsed.name,
            quantity=parsed.quantity,
            unit=parsed.unit,
            category=category,
            source=Product.SOURCE_EMAIL if source == Receipt.SOURCE_EMAIL else Product.SOURCE_RECEIPT,
        )
        suggestion = self.shelf_life.suggest(parsed.name)
        if suggestion:
            product.shelf_life_days = suggestion.days
            product.comment = f"Срок предложен по правилу: {suggestion.rule_name}"
        product.save()
        return product

    def _clean_text(self, text: str) -> str:
        return text.replace("\x00", "")

    def _refresh_receipt_status(self, receipt: Receipt) -> None:
        has_unknown = receipt.items.filter(is_food=False, category=FoodClassifier.UNKNOWN_CATEGORY).exists()
        receipt.status = "needs_review" if has_unknown else "processed"
        receipt.save(update_fields=["status"])


class EmailImportService:
    def __init__(self, source):
        self.source = source
        self.importer = ReceiptImportService(source.user)

    def run(self, limit: int = 20) -> int:
        connection = self._connect()
        processed = 0
        try:
            for mailbox in self._mailboxes(connection):
                processed += self._run_mailbox(connection, mailbox, limit)
            self.source.last_run_at = timezone.now()
            self.source.save(update_fields=["last_run_at"])
        finally:
            try:
                connection.logout()
            except Exception:
                pass
        return processed

    def _run_mailbox(self, connection, mailbox: bytes, limit: int) -> int:
        status, _ = connection.select(mailbox, readonly=True)
        if status != "OK":
            return 0
        _, data = connection.search(None, "ALL")
        ids = data[0].split()[-limit:]
        processed = 0
        mailbox_label = self._mailbox_label(mailbox)
        for uid in ids:
            uid_label = uid.decode("ascii", errors="ignore")
            external_id = uid_label if mailbox_label == "INBOX" else f"{mailbox_label}:{uid_label}"
            if ProcessingLog.objects.filter(user=self.source.user, source_type="email", external_id=external_id).exists():
                continue
            _, msg_data = connection.fetch(uid, "(RFC822)")
            message = email.message_from_bytes(msg_data[0][1])
            text = self._extract_text(message)
            if not self._matches_sender_filter(message, text):
                continue
            if not text.strip():
                self._log(external_id, ProcessingLog.STATUS_SKIPPED, "Текст чека не найден.")
                continue
            self.importer.import_text(text, source=Receipt.SOURCE_EMAIL)
            self._log(external_id, ProcessingLog.STATUS_SUCCESS, "Письмо импортировано.")
            processed += 1
        return processed

    def _mailboxes(self, connection) -> list[bytes]:
        status, data = connection.list()
        if status != "OK" or not data:
            return [b"INBOX"]
        mailboxes = []
        for row in data:
            if not row:
                continue
            name = self._parse_mailbox_name(row)
            if name and name not in mailboxes:
                mailboxes.append(name)
        return mailboxes or [b"INBOX"]

    def _parse_mailbox_name(self, row: bytes) -> bytes:
        parts = row.rsplit(b' "/" ', 1)
        if len(parts) != 2:
            return b""
        return parts[1].strip().strip(b'"')

    def _mailbox_label(self, mailbox: bytes) -> str:
        return mailbox.decode("ascii", errors="ignore") or "mailbox"

    def _matches_sender_filter(self, message: Message, text: str) -> bool:
        if not self.source.sender_filter:
            return True
        filters = [value.strip().lower() for value in self.source.sender_filter.split(",") if value.strip()]
        if not filters:
            return True
        searchable = "\n".join(
            [
                self._decode_header_value(message.get("From", "")),
                self._decode_header_value(message.get("Subject", "")),
                text,
            ]
        ).lower()
        return any(value in searchable for value in filters)

    def _decode_header_value(self, value: str) -> str:
        if not value:
            return ""
        return str(make_header(decode_header(value)))

    def _connect(self):
        if self.source.use_ssl:
            connection = imaplib.IMAP4_SSL(self.source.host, self.source.port)
        else:
            connection = imaplib.IMAP4(self.source.host, self.source.port)
        connection.login(self.source.username, self.source.password)
        return connection

    def _extract_text(self, message: Message) -> str:
        chunks = []
        if message.is_multipart():
            parts = message.walk()
        else:
            parts = [message]
        for part in parts:
            content_type = part.get_content_type()
            if content_type in {"text/plain", "text/html"}:
                payload = part.get_payload(decode=True)
                if not payload:
                    continue
                charset = part.get_content_charset() or "utf-8"
                try:
                    chunks.append(payload.decode(charset, errors="ignore"))
                except LookupError:
                    chunks.append(payload.decode("utf-8", errors="ignore"))
        return "\n".join(chunks).replace("\x00", "")

    def _log(self, external_id: str, status: str, message: str) -> None:
        try:
            ProcessingLog.objects.create(user=self.source.user, source_type="email", external_id=external_id, status=status, message=message)
        except IntegrityError:
            pass
