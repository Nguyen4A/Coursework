from django.core.management.base import BaseCommand

from notifications.services import NotificationService


class Command(BaseCommand):
    help = "Создает уведомления о продуктах, срок годности которых скоро истекает или уже истек."

    def handle(self, *args, **options):
        created = NotificationService().create_due_notifications()
        self.stdout.write(self.style.SUCCESS(f"Создано уведомлений: {created}"))
