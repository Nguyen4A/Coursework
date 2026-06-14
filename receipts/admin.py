from django.contrib import admin

from .models import EmailImportSource, ProcessingLog, ProductKeyword, Receipt, ReceiptItem


class ReceiptItemInline(admin.TabularInline):
    model = ReceiptItem
    extra = 0


@admin.register(Receipt)
class ReceiptAdmin(admin.ModelAdmin):
    list_display = ("id", "user", "source", "status", "created_at")
    list_filter = ("source", "status")
    search_fields = ("original_text", "user__username")
    inlines = (ReceiptItemInline,)


@admin.register(ReceiptItem)
class ReceiptItemAdmin(admin.ModelAdmin):
    list_display = ("normalized_name", "receipt", "quantity", "unit", "is_food", "category", "created_product")
    list_filter = ("is_food", "category")
    search_fields = ("raw_name", "normalized_name")


@admin.register(ProductKeyword)
class ProductKeywordAdmin(admin.ModelAdmin):
    list_display = ("word", "category", "is_food", "source", "owner", "created_at")
    list_filter = ("is_food", "source", "category")
    search_fields = ("word", "category", "owner__username")


@admin.register(EmailImportSource)
class EmailImportSourceAdmin(admin.ModelAdmin):
    list_display = ("name", "user", "host", "username", "is_active", "last_run_at")
    list_filter = ("is_active", "use_ssl")
    search_fields = ("name", "username", "host")


@admin.register(ProcessingLog)
class ProcessingLogAdmin(admin.ModelAdmin):
    list_display = ("source_type", "external_id", "user", "status", "created_at")
    list_filter = ("status", "source_type")
    search_fields = ("external_id", "message", "user__username")
