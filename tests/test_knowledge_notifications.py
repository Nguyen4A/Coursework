from django.contrib.auth.models import User
from django.test import TestCase
from django.utils import timezone

from knowledge.models import ShelfLifeRule
from knowledge.services import ShelfLifeService
from notifications.models import Notification
from notifications.services import NotificationService
from pantry.models import Product


class KnowledgeAndNotificationTests(TestCase):
    def setUp(self):
        self.user = User.objects.create_user("u", email="u@example.com", password="p")

    def test_shelf_life_exact_and_user_override(self):
        ShelfLifeRule.objects.create(product_name="молоко", shelf_life_days=5)
        ShelfLifeRule.objects.create(owner=self.user, product_name="молоко", shelf_life_days=2)
        suggestion = ShelfLifeService(self.user).suggest("молоко")
        self.assertEqual(suggestion.days, 2)

    def test_shelf_life_best_match(self):
        ShelfLifeRule.objects.create(product_name="курица", shelf_life_days=2, tags="мясо птица")
        suggestion = ShelfLifeService(self.user).suggest("курица охлажденная")
        self.assertEqual(suggestion.days, 2)

    def test_notifications_created(self):
        Product.objects.create(
            user=self.user,
            name="Йогурт",
            quantity=1,
            unit="pcs",
            purchase_date=timezone.localdate(),
            shelf_life_days=3,
        )
        created = NotificationService().create_due_notifications()
        self.assertEqual(created, 1)
        self.assertEqual(Notification.objects.get().notification_type, Notification.TYPE_3_DAYS)
