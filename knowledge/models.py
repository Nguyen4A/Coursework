from django.conf import settings
from django.db import models


class ShelfLifeRule(models.Model):
    owner = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, null=True, blank=True, related_name="shelf_life_rules")
    product_name = models.CharField("Название продукта", max_length=200)
    description = models.TextField("Описание", blank=True)
    shelf_life_days = models.PositiveIntegerField("Срок хранения, дней")
    storage_conditions = models.CharField("Условия хранения", max_length=200, blank=True)
    category = models.CharField("Категория", max_length=120, blank=True)
    tags = models.CharField("Теги", max_length=250, blank=True)
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ("product_name",)
        indexes = [
            models.Index(fields=("owner", "product_name")),
            models.Index(fields=("is_active",)),
        ]

    def __str__(self):
        scope = self.owner.get_username() if self.owner else "common"
        return f"{self.product_name} ({self.shelf_life_days} дн., {scope})"
