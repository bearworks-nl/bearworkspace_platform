from django.contrib import admin
from django.utils.html import format_html
from .models import SiteSettings


@admin.register(SiteSettings)
class SiteSettingsAdmin(admin.ModelAdmin):
    fields = ('logo', 'logo_preview', 'logo_dark', 'logo_dark_preview', 'logo_text', 'favicon')
    readonly_fields = ('logo_preview', 'logo_dark_preview')

    def logo_preview(self, obj):
        if obj.logo:
            return format_html(
                '<img src="{}" style="max-height:64px;max-width:200px;border-radius:6px;'
                'border:1px solid #ddd;padding:4px;background:#fff;" />',
                obj.logo.url
            )
        return '—'
    logo_preview.short_description = 'Current logo'

    def logo_dark_preview(self, obj):
        if obj.logo_dark:
            return format_html(
                '<img src="{}" style="max-height:64px;max-width:200px;border-radius:6px;'
                'border:1px solid #444;padding:4px;background:#0d0f14;" />',
                obj.logo_dark.url
            )
        return '—'
    logo_dark_preview.short_description = 'Current dark logo'

    def has_add_permission(self, request):
        return False

    def has_delete_permission(self, request, obj=None):
        return False

    def changelist_view(self, request, extra_context=None):
        obj = SiteSettings.get()
        return self.change_view(request, str(obj.pk), extra_context=extra_context)