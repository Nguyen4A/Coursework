from datetime import timedelta

from django.conf import settings
from django.db import models
from django.utils import timezone


class ProductCategory(models.Model):
    name = models.CharField("Название", max_length=120, unique=True)
    is_food_default = models.BooleanField("Пищевая категория", default=True)

    class Meta:
        ordering = ("name",)
        verbose_name = "Категория продукта"
        verbose_name_plural = "Категории продуктов"

    def __str__(self):
        return self.name


class Product(models.Model):
    STATUS_ACTIVE = "active"
    STATUS_EXPIRING_SOON = "expiring_soon"
    STATUS_EXPIRED = "expired"
    STATUS_NEEDS_REVIEW = "needs_review"
    STATUS_CHOICES = [
        (STATUS_ACTIVE, "Свежий"),
        (STATUS_EXPIRING_SOON, "Скоро истекает"),
        (STATUS_EXPIRED, "Просрочен"),
        (STATUS_NEEDS_REVIEW, "Требует подтверждения"),
    ]

    SOURCE_MANUAL = "manual"
    SOURCE_RECEIPT = "receipt"
    SOURCE_EMAIL = "email"
    SOURCE_CHOICES = [
        (SOURCE_MANUAL, "Вручную"),
        (SOURCE_RECEIPT, "Чек"),
        (SOURCE_EMAIL, "Письмо"),
    ]

    UNIT_CHOICES = [
        ("pcs", "шт."),
        ("g", "г"),
        ("kg", "кг"),
        ("ml", "мл"),
        ("l", "л"),
        ("pack", "упаковка"),
    ]

    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="products")
    name = models.CharField("Название", max_length=200)
    quantity = models.DecimalField("Количество", max_digits=8, decimal_places=2, default=1)
    unit = models.CharField("Единица", max_length=20, choices=UNIT_CHOICES, default="pcs")
    category = models.ForeignKey(ProductCategory, on_delete=models.SET_NULL, null=True, blank=True)
    purchase_date = models.DateField("Дата покупки", default=timezone.localdate)
    shelf_life_days = models.PositiveIntegerField("Срок годности, дней", null=True, blank=True)
    expiration_date = models.DateField("Дата истечения", null=True, blank=True)
    status = models.CharField("Статус", max_length=20, choices=STATUS_CHOICES, default=STATUS_NEEDS_REVIEW)
    comment = models.TextField("Комментарий", blank=True)
    source = models.CharField("Источник", max_length=20, choices=SOURCE_CHOICES, default=SOURCE_MANUAL)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ("expiration_date", "name")
        indexes = [
            models.Index(fields=("user", "status")),
            models.Index(fields=("user", "expiration_date")),
        ]

    def __str__(self):
        return self.name

    def recalculate_expiration(self):
        if self.shelf_life_days is not None:
            self.expiration_date = self.purchase_date + timedelta(days=self.shelf_life_days)

    def refresh_status(self):
        if not self.expiration_date or self.shelf_life_days is None:
            self.status = self.STATUS_NEEDS_REVIEW
            return
        today = timezone.localdate()
        if self.expiration_date < today:
            self.status = self.STATUS_EXPIRED
        elif self.expiration_date <= today + timedelta(days=3):
            self.status = self.STATUS_EXPIRING_SOON
        else:
            self.status = self.STATUS_ACTIVE

    def save(self, *args, **kwargs):
        if self.shelf_life_days is not None and not self.expiration_date:
            self.recalculate_expiration()
        self.refresh_status()
        super().save(*args, **kwargs)
