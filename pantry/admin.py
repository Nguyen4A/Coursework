from django.contrib import admin

from .models import Product, ProductCategory


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
