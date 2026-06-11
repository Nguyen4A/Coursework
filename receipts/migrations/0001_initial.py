import django.db.models.deletion
from django.conf import settings
from django.db import migrations, models


class Migration(migrations.Migration):
    initial = True
    dependencies = [
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
        ("pantry", "0001_initial"),
    ]
    operations = [
        migrations.CreateModel(
            name="EmailImportSource",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("name", models.CharField(default="Основная почта", max_length=120)),
                ("host", models.CharField(max_length=200)),
                ("port", models.PositiveIntegerField(default=993)),
                ("username", models.CharField(max_length=200)),
                ("password", models.CharField(max_length=300)),
                ("use_ssl", models.BooleanField(default=True)),
                ("sender_filter", models.CharField(blank=True, help_text="Например: receipt, чек, магазин", max_length=250)),
                ("is_active", models.BooleanField(default=True)),
                ("last_run_at", models.DateTimeField(blank=True, null=True)),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                ("user", models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name="email_sources", to=settings.AUTH_USER_MODEL)),
            ],
        ),
        migrations.CreateModel(
            name="ProcessingLog",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("source_type", models.CharField(max_length=30)),
                ("external_id", models.CharField(max_length=250)),
                ("status", models.CharField(choices=[("success", "Успешно"), ("skipped", "Пропущено"), ("error", "Ошибка")], max_length=20)),
                ("message", models.TextField(blank=True)),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                ("user", models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, to=settings.AUTH_USER_MODEL)),
            ],
            options={"ordering": ("-created_at",), "unique_together": {("user", "source_type", "external_id")}},
        ),
        migrations.CreateModel(
            name="Receipt",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("source", models.CharField(choices=[("text", "Текст"), ("file", "Файл"), ("email", "Письмо")], max_length=20)),
                ("original_text", models.TextField(blank=True)),
                ("file", models.FileField(blank=True, upload_to="receipts/")),
                ("status", models.CharField(default="processed", max_length=30)),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                ("user", models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name="receipts", to=settings.AUTH_USER_MODEL)),
            ],
        ),
        migrations.CreateModel(
            name="ReceiptItem",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("raw_name", models.CharField(max_length=250)),
                ("normalized_name", models.CharField(max_length=200)),
                ("quantity", models.DecimalField(decimal_places=2, default=1, max_digits=8)),
                ("unit", models.CharField(default="pcs", max_length=20)),
                ("is_food", models.BooleanField(default=True)),
                ("category", models.CharField(blank=True, max_length=120)),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                ("created_product", models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, to="pantry.product")),
                ("receipt", models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name="items", to="receipts.receipt")),
            ],
        ),
    ]
