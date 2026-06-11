import django.db.models.deletion
import django.utils.timezone
from django.conf import settings
from django.db import migrations, models


class Migration(migrations.Migration):
    initial = True
    dependencies = [migrations.swappable_dependency(settings.AUTH_USER_MODEL)]
    operations = [
        migrations.CreateModel(
            name="ProductCategory",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("name", models.CharField(max_length=120, unique=True, verbose_name="Название")),
                ("is_food_default", models.BooleanField(default=True, verbose_name="Пищевая категория")),
            ],
            options={"verbose_name": "Категория продукта", "verbose_name_plural": "Категории продуктов", "ordering": ("name",)},
        ),
        migrations.CreateModel(
            name="Product",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("name", models.CharField(max_length=200, verbose_name="Название")),
                ("quantity", models.DecimalField(decimal_places=2, default=1, max_digits=8, verbose_name="Количество")),
                ("unit", models.CharField(choices=[("pcs", "шт."), ("g", "г"), ("kg", "кг"), ("ml", "мл"), ("l", "л"), ("pack", "упаковка")], default="pcs", max_length=20, verbose_name="Единица")),
                ("purchase_date", models.DateField(default=django.utils.timezone.localdate, verbose_name="Дата покупки")),
                ("shelf_life_days", models.PositiveIntegerField(blank=True, null=True, verbose_name="Срок годности, дней")),
                ("expiration_date", models.DateField(blank=True, null=True, verbose_name="Дата истечения")),
                ("status", models.CharField(choices=[("active", "Свежий"), ("expiring_soon", "Скоро истекает"), ("expired", "Просрочен"), ("needs_review", "Требует подтверждения")], default="needs_review", max_length=20, verbose_name="Статус")),
                ("comment", models.TextField(blank=True, verbose_name="Комментарий")),
                ("source", models.CharField(choices=[("manual", "Вручную"), ("receipt", "Чек"), ("email", "Письмо")], default="manual", max_length=20, verbose_name="Источник")),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                ("updated_at", models.DateTimeField(auto_now=True)),
                ("category", models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, to="pantry.productcategory")),
                ("user", models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name="products", to=settings.AUTH_USER_MODEL)),
            ],
            options={"ordering": ("expiration_date", "name")},
        ),
        migrations.AddIndex(model_name="product", index=models.Index(fields=["user", "status"], name="pantry_prod_user_id_ee0680_idx")),
        migrations.AddIndex(model_name="product", index=models.Index(fields=["user", "expiration_date"], name="pantry_prod_user_id_bff51e_idx")),
    ]
