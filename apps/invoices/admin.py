from django.contrib import admin
from .models import Invoice, Transaction, Category, CategoryRule


@admin.register(Invoice)
class InvoiceAdmin(admin.ModelAdmin):
    list_display = ['filename', 'year', 'month', 'uploaded_at']
    list_filter = ['year', 'month']


@admin.register(Transaction)
class TransactionAdmin(admin.ModelAdmin):
    list_display = ['date', 'description', 'amount', 'category', 'invoice']
    list_filter = ['category', 'invoice']
    search_fields = ['description']


@admin.register(Category)
class CategoryAdmin(admin.ModelAdmin):
    list_display = ['name', 'icon', 'color']


@admin.register(CategoryRule)
class CategoryRuleAdmin(admin.ModelAdmin):
    list_display = ['keyword', 'category', 'priority']
    list_filter = ['category']
