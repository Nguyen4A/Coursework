from datetime import timedelta

from django.contrib.auth.models import User
from django.test import TestCase
from django.urls import reverse
from django.utils import timezone

from pantry.models import Product


class PantryTests(TestCase):
    def setUp(self):
        self.user = User.objects.create_user("u", password="p")
        self.client.force_login(self.user)

    def test_create_product_calculates_expiration(self):
        today = timezone.localdate()
        response = self.client.post(
            reverse("pantry:product_create"),
            {
                "name": "Молоко",
                "quantity": "1",
                "unit": "l",
                "category_name": "молочные продукты",
                "purchase_date": today,
                "shelf_life_days": "5",
                "expiration_date": "",
                "comment": "",
                "source": "manual",
            },
        )
        self.assertRedirects(response, reverse("pantry:product_list"))
        product = Product.objects.get(user=self.user)
        self.assertEqual(product.expiration_date, today + timedelta(days=5))
