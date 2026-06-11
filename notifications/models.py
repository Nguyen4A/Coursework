from django.conf import settings
from django.db import models


class Notification(models.Model):
    TYPE_3_DAYS = "3_days"
    TYPE_1_DAY = "1_day"
    TYPE_EXPIRED = "expired"
    TYPE_CHOICES = [(TYPE_3_DAYS, "Через 3 дня"), (TYPE_1_DAY, "Через 1 день"), (TYPE_EXPIRED, "Просрочено")]

    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="notifications")
    product = models.ForeignKey("pantry.Product", on_delete=models.CASCADE, related_name="notifications")
    notification_type = models.CharField(max_length=20, choices=TYPE_CHOICES)
    message = models.TextField()
    is_read = models.BooleanField(default=False)
    email_sent = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        unique_together = ("product", "notification_type")
        ordering = ("-created_at",)

    def __str__(self):
        return self.message
