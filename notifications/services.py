from datetime import timedelta

from django.core.mail import send_mail
from django.utils import timezone

from accounts.models import UserProfile
from pantry.models import Product

from .models import Notification


class NotificationService:
    TARGETS = {
        3: Notification.TYPE_3_DAYS,
        1: Notification.TYPE_1_DAY,
        -1: Notification.TYPE_EXPIRED,
    }

    def create_due_notifications(self) -> int:
        today = timezone.localdate()
        created = 0
        products = Product.objects.exclude(expiration_date__isnull=True).select_related("user")
        for product in products:
            delta = (product.expiration_date - today).days
            notification_type = self.TARGETS.get(delta)
            if delta < 0:
                notification_type = Notification.TYPE_EXPIRED
            if not notification_type:
                continue
            notification, was_created = Notification.objects.get_or_create(
                product=product,
                notification_type=notification_type,
                defaults={"user": product.user, "message": self._message(product, delta)},
            )
            if was_created:
                self._send_email(notification)
                created += 1
        return created

    def _message(self, product: Product, delta: int) -> str:
        if delta < 0:
            return f"Срок годности продукта «{product.name}» истек {product.expiration_date}."
        if delta == 1:
            return f"Срок годности продукта «{product.name}» истекает завтра."
        return f"Срок годности продукта «{product.name}» истекает через {delta} дня."

    def _send_email(self, notification: Notification) -> None:
        profile, _ = UserProfile.objects.get_or_create(user=notification.user)
        if not profile.email_notifications or not notification.user.email:
            return
        try:
            send_mail(
                "Smart Fridge: срок годности",
                notification.message,
                None,
                [notification.user.email],
                fail_silently=True,
            )
            notification.email_sent = True
            notification.save(update_fields=["email_sent"])
        except Exception:
            pass
