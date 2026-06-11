from django.contrib import admin

from .models import Notification


@admin.register(Notification)
class NotificationAdmin(admin.ModelAdmin):
    list_display = ("user", "product", "notification_type", "is_read", "email_sent", "created_at")
    list_filter = ("notification_type", "is_read", "email_sent")
    search_fields = ("message", "user__username", "product__name")
