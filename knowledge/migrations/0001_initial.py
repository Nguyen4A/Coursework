import django.db.models.deletion
from django.conf import settings
from django.db import migrations, models


class Migration(migrations.Migration):
    initial = True
    dependencies = [migrations.swappable_dependency(settings.AUTH_USER_MODEL)]
    operations = [
        migrations.CreateModel(
            name="ShelfLifeRule",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("product_name", models.CharField(max_length=200, verbose_name="Название продукта")),
                ("description", models.TextField(blank=True, verbose_name="Описание")),
                ("shelf_life_days", models.PositiveIntegerField(verbose_name="Срок хранения, дней")),
                ("storage_conditions", models.CharField(blank=True, max_length=200, verbose_name="Условия хранения")),
                ("category", models.CharField(blank=True, max_length=120, verbose_name="Категория")),
                ("tags", models.CharField(blank=True, max_length=250, verbose_name="Теги")),
                ("is_active", models.BooleanField(default=True)),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                ("updated_at", models.DateTimeField(auto_now=True)),
                ("owner", models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.CASCADE, related_name="shelf_life_rules", to=settings.AUTH_USER_MODEL)),
            ],
            options={"ordering": ("product_name",)},
        ),
        migrations.AddIndex(model_name="shelfliferule", index=models.Index(fields=["owner", "product_name"], name="knowledge_s_owner_i_86bb94_idx")),
        migrations.AddIndex(model_name="shelfliferule", index=models.Index(fields=["is_active"], name="knowledge_s_is_acti_036ff1_idx")),
    ]
