from django.conf import settings
from django.db import models


class Receipt(models.Model):
    SOURCE_TEXT = "text"
    SOURCE_FILE = "file"
    SOURCE_EMAIL = "email"
    SOURCE_CHOICES = [(SOURCE_TEXT, "Текст"), (SOURCE_FILE, "Файл"), (SOURCE_EMAIL, "Письмо")]

    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="receipts")
    source = models.CharField(max_length=20, choices=SOURCE_CHOICES)
    original_text = models.TextField(blank=True)
    file = models.FileField(upload_to="receipts/", blank=True)
    status = models.CharField(max_length=30, default="processed")
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"Чек #{self.pk} ({self.get_source_display()})"


class ReceiptItem(models.Model):
    receipt = models.ForeignKey(Receipt, on_delete=models.CASCADE, related_name="items")
    raw_name = models.CharField(max_length=250)
    normalized_name = models.CharField(max_length=200)
    quantity = models.DecimalField(max_digits=8, decimal_places=2, default=1)
    unit = models.CharField(max_length=20, default="pcs")
    is_food = models.BooleanField(default=True)
    category = models.CharField(max_length=120, blank=True)
    created_product = models.ForeignKey("pantry.Product", null=True, blank=True, on_delete=models.SET_NULL)
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return self.normalized_name


class EmailImportSource(models.Model):
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="email_sources")
    name = models.CharField(max_length=120, default="Основная почта")
    host = models.CharField(max_length=200)
    port = models.PositiveIntegerField(default=993)
    username = models.CharField(max_length=200)
    password = models.CharField(max_length=300)
    use_ssl = models.BooleanField(default=True)
    sender_filter = models.CharField(max_length=250, blank=True, help_text="Например: receipt, чек, магазин")
    is_active = models.BooleanField(default=True)
    last_run_at = models.DateTimeField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.name}: {self.username}"


class ProcessingLog(models.Model):
    STATUS_SUCCESS = "success"
    STATUS_SKIPPED = "skipped"
    STATUS_ERROR = "error"
    STATUS_CHOICES = [(STATUS_SUCCESS, "Успешно"), (STATUS_SKIPPED, "Пропущено"), (STATUS_ERROR, "Ошибка")]

    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE)
    source_type = models.CharField(max_length=30)
    external_id = models.CharField(max_length=250)
    status = models.CharField(max_length=20, choices=STATUS_CHOICES)
    message = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        unique_together = ("user", "source_type", "external_id")
        ordering = ("-created_at",)

    def __str__(self):
        return f"{self.source_type}:{self.external_id} {self.status}"
