from django.contrib import admin
from .models import Service, RecastConfig, Windows365Config, IntuneConfig


@admin.register(Service)
class ServiceAdmin(admin.ModelAdmin):
    list_display = ('service_type', 'environment', 'status', 'enabled')
    list_filter = ('service_type', 'status', 'enabled')


admin.site.register(RecastConfig)
admin.site.register(Windows365Config)
admin.site.register(IntuneConfig)
