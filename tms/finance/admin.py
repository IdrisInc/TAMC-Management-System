from django.contrib import admin
from .models import FinancialRequest, Item

class ItemInline(admin.TabularInline):
    model = Item
    extra = 1

class FinancialRequestAdmin(admin.ModelAdmin):
    inlines = [ItemInline]
    list_display = ['amount_numeric', 'purpose', 'total_request', 'display_approved_by_production', 'display_approved_by_technical_manager', 'display_approved_by_finance', 'display_approved_by_treasurer', 'display_approved_by_cashier', 'wef', 'account_to_charge', 'account_code']
    list_filter = ['approved_by_production', 'approved_by_technical_manager', 'approved_by_finance', 'approved_by_treasurer', 'approved_by_cashier']
    search_fields = ['purpose']

    def display_approved_by_production(self, obj):
        return ", ".join([user.username for user in obj.approved_by_production.all()])
    display_approved_by_production.short_description = 'Approved by Production'

    def display_approved_by_technical_manager(self, obj):
        return ", ".join([user.username for user in obj.approved_by_technical_manager.all()])
    display_approved_by_technical_manager.short_description = 'Approved by Technical Manager'

    def display_approved_by_finance(self, obj):
        return ", ".join([user.username for user in obj.approved_by_finance.all()])
    display_approved_by_finance.short_description = 'Approved by Finance'

    def display_approved_by_treasurer(self, obj):
        return ", ".join([user.username for user in obj.approved_by_treasurer.all()])
    display_approved_by_treasurer.short_description = 'Approved by Treasurer'

    def display_approved_by_cashier(self, obj):
        return ", ".join([user.username for user in obj.approved_by_cashier.all()])
    display_approved_by_cashier.short_description = 'Approved by Cashier'

admin.site.register(FinancialRequest, FinancialRequestAdmin)
admin.site.register(Item)
