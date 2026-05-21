from django.contrib import admin
from .models import Environment, EnvironmentMembership

@admin.register(Environment)
class EnvironmentAdmin(admin.ModelAdmin):
    list_display = ('name', 'owner', 'status', 'created_at')
    list_filter = ('status',)
    search_fields = ('name', 'owner__email')

admin.site.register(EnvironmentMembership)
