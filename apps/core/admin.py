from django.contrib import admin
from django.utils.html import format_html
from .models import SiteSettings


@admin.register(SiteSettings)
class SiteSettingsAdmin(admin.ModelAdmin):
    """
    Superadmin-only singleton admin for site branding.
    Hides the "Add" button and always redirects to the single instance.
    """
    fields = ('logo', 'logo_preview', 'logo_text', 'favicon')
    readonly_fields = ('logo_preview',)

    def logo_preview(self, obj):
        if obj.logo:
            return format_html(
                '<img src="{}" style="max-height:64px;max-width:200px;border-radius:6px;'
                'border:1px solid #ddd;padding:4px;background:#fff;" />',
                obj.logo.url
            )
        return '—'
    logo_preview.short_description = 'Current logo'

    def has_add_permission(self, request):
        return False

    def has_delete_permission(self, request, obj=None):
        return False

    def changelist_view(self, request, extra_context=None):
        """Skip the list view and go straight to the single instance."""
        obj = SiteSettings.get()
        return self.change_view(request, str(obj.pk), extra_context=extra_context)
