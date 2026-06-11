from django.test import TestCase
from django.urls import reverse


class AccountsTests(TestCase):
    def test_registration_and_login(self):
        response = self.client.post(
            reverse("accounts:register"),
            {
                "username": "anna",
                "email": "anna@example.com",
                "full_name": "Anna",
                "password1": "StrongPass123!",
                "password2": "StrongPass123!",
            },
        )
        self.assertRedirects(response, reverse("pantry:product_list"))
        response = self.client.get(reverse("accounts:profile"))
        self.assertContains(response, "Профиль")
