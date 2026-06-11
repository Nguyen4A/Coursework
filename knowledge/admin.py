from django.contrib import admin

from .models import ShelfLifeRule


@admin.register(ShelfLifeRule)
class ShelfLifeRuleAdmin(admin.ModelAdmin):
    list_display = ("product_name", "owner", "shelf_life_days", "category", "storage_conditions", "is_active")
    list_filter = ("is_active", "category", "owner")
    search_fields = ("product_name", "description", "tags", "category")
