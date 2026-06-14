from django.contrib import admin

from .models import Product, ProductCategory, ProductUsageEvent, RecipeTemplate


@admin.register(ProductCategory)
class ProductCategoryAdmin(admin.ModelAdmin):
    list_display = ("name", "is_food_default")
    search_fields = ("name",)
    list_filter = ("is_food_default",)


@admin.register(Product)
class ProductAdmin(admin.ModelAdmin):
    list_display = ("name", "user", "quantity", "unit", "category", "expiration_date", "status", "source")
    list_filter = ("status", "source", "category")
    search_fields = ("name", "user__username", "comment")
    date_hierarchy = "expiration_date"


@admin.register(RecipeTemplate)
class RecipeTemplateAdmin(admin.ModelAdmin):
    list_display = ("title", "category", "prioritize_expiring", "is_active")
    list_filter = ("prioritize_expiring", "is_active", "category")
    search_fields = ("title", "tags", "steps")


@admin.register(ProductUsageEvent)
class ProductUsageEventAdmin(admin.ModelAdmin):
    list_display = ("product_name_snapshot", "user", "action", "quantity", "category_snapshot", "wasted_expired", "created_at")
    list_filter = ("action", "wasted_expired", "category_snapshot")
    search_fields = ("product_name_snapshot", "user__username")
