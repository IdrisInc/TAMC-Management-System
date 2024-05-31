from django.contrib import admin
from .models import FinancialRequest, Item

class ItemInline(admin.TabularInline):
    model = Item
    extra = 1

class FinancialRequestAdmin(admin.ModelAdmin):
    inlines = [ItemInline]
    list_display = ['amount_numeric', 'purpose', 'total_request', 'approved_by_production', 'approved_by_technical_manager', 'approved_by_finance', 'approved_by_treasurer', 'approved_by_cashier', 'wef', 'account_to_charge', 'account_code']
    list_filter = ['approved_by_production', 'approved_by_technical_manager', 'approved_by_finance', 'approved_by_treasurer', 'approved_by_cashier']
    search_fields = ['purpose']
    

admin.site.register(FinancialRequest, FinancialRequestAdmin)
admin.site.register(Item)
# Register your models here.
