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
            models.Index(fields=("user", "status"), name="pantry_prod_user_id_ee0680_idx"),
            models.Index(fields=("user", "expiration_date"), name="pantry_prod_user_id_bff51e_idx"),
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


class RecipeTemplate(models.Model):
    title = models.CharField("Название", max_length=160)
    required_ingredients = models.JSONField("Ключевые ингредиенты", default=list)
    steps = models.TextField("Шаги")
    category = models.CharField("Категория", max_length=120, blank=True)
    tags = models.CharField("Теги", max_length=250, blank=True)
    prioritize_expiring = models.BooleanField("Приоритет скоропортящимся", default=True)
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ("title",)
        indexes = [
            models.Index(fields=("is_active", "prioritize_expiring")),
        ]

    def __str__(self):
        return self.title


class ProductUsageEvent(models.Model):
    ACTION_USED = "used"
    ACTION_WASTED = "wasted"
    ACTION_CHOICES = [
        (ACTION_USED, "Использовал"),
        (ACTION_WASTED, "Выкинул"),
    ]

    product = models.ForeignKey(Product, null=True, blank=True, on_delete=models.SET_NULL, related_name="usage_events")
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="product_usage_events")
    action = models.CharField(max_length=20, choices=ACTION_CHOICES)
    quantity = models.DecimalField(max_digits=8, decimal_places=2, default=1)
    category_snapshot = models.CharField(max_length=120, blank=True)
    product_name_snapshot = models.CharField(max_length=200)
    expiration_date_snapshot = models.DateField(null=True, blank=True)
    wasted_expired = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ("-created_at",)
        indexes = [
            models.Index(fields=("user", "action", "created_at")),
            models.Index(fields=("user", "wasted_expired")),
        ]

    def __str__(self):
        return f"{self.product_name_snapshot}: {self.action}"
