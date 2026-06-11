from django import forms

from .models import ShelfLifeRule


class ShelfLifeRuleForm(forms.ModelForm):
    class Meta:
        model = ShelfLifeRule
        fields = ("product_name", "description", "shelf_life_days", "storage_conditions", "category", "tags", "is_active")
        widgets = {"description": forms.Textarea(attrs={"rows": 3})}
