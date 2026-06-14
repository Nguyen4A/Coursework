import django.db.models.deletion
from django.conf import settings
from django.db import migrations, models


FOOD_WORDS = {
    "молоко": "молочные продукты",
    "кефир": "молочные продукты",
    "сыр": "молочные продукты",
    "йогурт": "молочные продукты",
    "творог": "молочные продукты",
    "сметана": "молочные продукты",
    "сливки": "молочные продукты",
    "ряженка": "молочные продукты",
    "айран": "молочные продукты",
    "хлеб": "хлеб",
    "батон": "хлеб",
    "лаваш": "хлеб",
    "булочка": "хлеб",
    "курица": "мясо",
    "говядина": "мясо",
    "свинина": "мясо",
    "индейка": "мясо",
    "фарш": "мясо",
    "колбаса": "мясо",
    "сосиска": "мясо",
    "рыба": "рыба",
    "лосось": "рыба",
    "тунец": "рыба",
    "креветка": "рыба",
    "яйцо": "яйца",
    "яблоко": "фрукты",
    "банан": "фрукты",
    "апельсин": "фрукты",
    "груша": "фрукты",
    "виноград": "фрукты",
    "лимон": "фрукты",
    "картофель": "овощи",
    "томат": "овощи",
    "помидор": "овощи",
    "огурец": "овощи",
    "морковь": "овощи",
    "лук": "овощи",
    "капуста": "овощи",
    "перец": "овощи",
    "свекла": "овощи",
    "рис": "крупы",
    "гречка": "крупы",
    "овсянка": "крупы",
    "пшено": "крупы",
    "макароны": "бакалея",
    "масло": "бакалея",
    "орех": "бакалея",
    "сухофрукт": "бакалея",
    "коктейль": "бакалея",
    "мука": "бакалея",
    "сахар": "бакалея",
    "соль": "бакалея",
    "чай": "бакалея",
    "кофе": "бакалея",
    "сок": "напитки",
    "вода": "напитки",
    "морс": "напитки",
    "компот": "напитки",
}

NON_FOOD_WORDS = {
    "пакет",
    "салфетки",
    "шампунь",
    "мыло",
    "гель",
    "зубная",
    "порошок",
    "батарейка",
    "лампа",
    "бумага",
    "крем",
    "дезодорант",
}


def seed_keywords(apps, schema_editor):
    ProductKeyword = apps.get_model("receipts", "ProductKeyword")
    for word, category in FOOD_WORDS.items():
        ProductKeyword.objects.get_or_create(
            owner=None,
            word=word.replace("ё", "е"),
            defaults={"category": category, "is_food": True, "source": "system"},
        )
    for word in NON_FOOD_WORDS:
        ProductKeyword.objects.get_or_create(
            owner=None,
            word=word.replace("ё", "е"),
            defaults={"category": "не пищевое", "is_food": False, "source": "system"},
        )


class Migration(migrations.Migration):
    dependencies = [
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
        ("receipts", "0001_initial"),
    ]

    operations = [
        migrations.CreateModel(
            name="ProductKeyword",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("word", models.CharField(max_length=120, verbose_name="Ключевое слово")),
                ("category", models.CharField(blank=True, max_length=120, verbose_name="Категория")),
                ("is_food", models.BooleanField(default=True, verbose_name="Это продукт")),
                ("source", models.CharField(choices=[("system", "Системное"), ("user", "Пользовательское")], default="system", max_length=20, verbose_name="Источник")),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                ("owner", models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.CASCADE, related_name="product_keywords", to=settings.AUTH_USER_MODEL)),
            ],
            options={
                "verbose_name": "Ключевое слово продукта",
                "verbose_name_plural": "Ключевые слова продуктов",
                "ordering": ("word",),
                "unique_together": {("owner", "word")},
            },
        ),
        migrations.AddIndex(model_name="productkeyword", index=models.Index(fields=["owner", "word"], name="receipts_pr_owner_i_533b9c_idx")),
        migrations.AddIndex(model_name="productkeyword", index=models.Index(fields=["is_food", "word"], name="receipts_pr_is_food_4c4b17_idx")),
        migrations.RunPython(seed_keywords, migrations.RunPython.noop),
    ]
