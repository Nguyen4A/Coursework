from django.conf import settings
from django.db import models


class UserProfile(models.Model):
    user = models.OneToOneField(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="profile")
    full_name = models.CharField("Имя", max_length=150, blank=True)
    email_notifications = models.BooleanField("Email-уведомления", default=True)
    notification_days = models.PositiveSmallIntegerField("За сколько дней предупреждать", default=3)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return self.full_name or self.user.get_username()
