from datetime import timedelta

from django.contrib.auth.models import User
from django.test import TestCase
from django.urls import reverse
from django.utils import timezone

from pantry.models import Product, ProductCategory, ProductUsageEvent, RecipeTemplate
from pantry.services import RecipeSuggestionService, WasteStatsService


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

    def test_product_form_has_category_suggestions(self):
        ProductCategory.objects.create(name="заморозка")

        response = self.client.get(reverse("pantry:product_create"))

        suggestions = response.context["form"].category_suggestions
        self.assertIn("бакалея", suggestions)
        self.assertIn("заморозка", suggestions)
        self.assertContains(response, "category-suggestions")

    def test_eat_first_sort_prioritizes_expiring_and_old_products(self):
        today = timezone.localdate()
        fresh = Product.objects.create(user=self.user, name="Рис", quantity=1, unit="pcs", purchase_date=today, shelf_life_days=100)
        urgent = Product.objects.create(user=self.user, name="Йогурт", quantity=1, unit="pcs", purchase_date=today, shelf_life_days=1)
        old_many = Product.objects.create(user=self.user, name="Картофель", quantity=5, unit="pcs", purchase_date=today - timedelta(days=40), shelf_life_days=60)

        response = self.client.get(reverse("pantry:product_list"), {"sort": "priority"})

        products = list(response.context["products"])
        self.assertEqual(products[0], urgent)
        self.assertIn(old_many, products[:2])
        self.assertIn(fresh, products)
        self.assertTrue(products[0].priority_reasons)

    def test_recipe_suggestions_match_existing_products(self):
        RecipeTemplate.objects.create(
            title="Омлет",
            required_ingredients=["яйцо", "молоко", "сыр"],
            steps="Смешать и приготовить.",
            category="завтрак",
        )
        today = timezone.localdate()
        Product.objects.create(user=self.user, name="Яйцо куриное", quantity=6, unit="pcs", purchase_date=today, shelf_life_days=1)
        Product.objects.create(user=self.user, name="Молоко", quantity=1, unit="l", purchase_date=today, shelf_life_days=2)
        Product.objects.create(user=self.user, name="Сыр", quantity=1, unit="pcs", purchase_date=today, shelf_life_days=10)

        suggestions = RecipeSuggestionService(self.user).suggest()

        self.assertEqual(suggestions[0].template.title, "Омлет")
        self.assertTrue(suggestions[0].can_cook)
        self.assertIn("яйцо", suggestions[0].expiring)

    def test_usage_events_feed_waste_stats(self):
        category = ProductCategory.objects.create(name="молочные продукты")
        expired = Product.objects.create(
            user=self.user,
            name="Кефир",
            quantity=1,
            unit="pcs",
            category=category,
            purchase_date=timezone.localdate() - timedelta(days=5),
            shelf_life_days=1,
        )
        used = Product.objects.create(user=self.user, name="Хлеб", quantity=1, unit="pcs", purchase_date=timezone.localdate(), shelf_life_days=3)

        self.client.post(reverse("pantry:product_mark_wasted", args=[expired.pk]))
        self.client.post(reverse("pantry:product_mark_used", args=[used.pk]))

        stats = WasteStatsService(self.user).build()
        self.assertEqual(stats["used_count"], 1)
        self.assertEqual(stats["wasted_count"], 1)
        self.assertEqual(stats["wasted_expired_count"], 1)
        self.assertEqual(stats["waste_percent"], 50.0)
        self.assertIn("молочные продукты", stats["recommendation"])
        self.assertEqual(ProductUsageEvent.objects.filter(user=self.user).count(), 2)
