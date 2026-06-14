from django import forms

from .models import Product, ProductCategory


class ProductForm(forms.ModelForm):
    BASE_CATEGORIES = [
        "молочные продукты",
        "хлеб",
        "мясо",
        "рыба",
        "яйца",
        "фрукты",
        "овощи",
        "крупы",
        "бакалея",
        "напитки",
        "Продукты",
    ]

    category_name = forms.CharField(label="Категория", max_length=120, required=False)

    class Meta:
        model = Product
        fields = (
            "name",
            "quantity",
            "unit",
            "category_name",
            "purchase_date",
            "shelf_life_days",
            "expiration_date",
            "comment",
            "source",
        )
        widgets = {
            "purchase_date": forms.DateInput(attrs={"type": "date"}),
            "expiration_date": forms.DateInput(attrs={"type": "date"}),
            "comment": forms.Textarea(attrs={"rows": 3}),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields["category_name"].widget.attrs.update(
            {
                "autocomplete": "off",
                "data-category-autocomplete": "1",
                "placeholder": "Начните вводить, например: бакалея",
            }
        )
        existing_categories = ProductCategory.objects.values_list("name", flat=True)
        self.category_suggestions = sorted({*self.BASE_CATEGORIES, *existing_categories}, key=str.casefold)
        if self.instance and self.instance.category:
            self.fields["category_name"].initial = self.instance.category.name

    def clean(self):
        cleaned = super().clean()
        shelf_life_days = cleaned.get("shelf_life_days")
        expiration_date = cleaned.get("expiration_date")
        if shelf_life_days is None and expiration_date is None:
            self.add_error("shelf_life_days", "Укажите срок годности или дату истечения.")
        return cleaned

    def save(self, commit=True):
        product = super().save(commit=False)
        category_name = self.cleaned_data.get("category_name", "").strip()
        product.category = None
        if category_name:
            product.category, _ = ProductCategory.objects.get_or_create(name=category_name)
        if "expiration_date" in self.changed_data and product.expiration_date and product.purchase_date:
            days = (product.expiration_date - product.purchase_date).days
            product.shelf_life_days = days if days >= 0 else None
        elif product.shelf_life_days is not None and {"purchase_date", "shelf_life_days"} & set(self.changed_data):
            product.expiration_date = None
            product.recalculate_expiration()
        if commit:
            product.save()
        return product
