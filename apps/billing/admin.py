from django.contrib import admin
from .models import Plan, Subscription, Invoice, UsageSnapshot


@admin.register(Plan)
class PlanAdmin(admin.ModelAdmin):
    list_display = ('name', 'service', 'price_per_unit', 'unit_label', 'billing_period', 'is_active')
    list_filter = ('billing_period', 'is_active')
    search_fields = ('name',)
    autocomplete_fields = []

    def get_queryset(self, request):
        return super().get_queryset(request).select_related('service', 'service__environment')


@admin.register(Subscription)
class SubscriptionAdmin(admin.ModelAdmin):
    list_display = ('user', 'plan', 'service', 'status', 'created_at')
    list_filter = ('status',)
    search_fields = ('user__email',)


@admin.register(Invoice)
class InvoiceAdmin(admin.ModelAdmin):
    list_display = ('invoice_number', 'user', 'amount', 'status', 'created_at')
    list_filter = ('status',)
    search_fields = ('invoice_number', 'user__email')

@admin.register(UsageSnapshot)
class UsageSnapshotAdmin(admin.ModelAdmin):
    list_display = ('subscription', 'quantity', 'period_start', 'period_end')
