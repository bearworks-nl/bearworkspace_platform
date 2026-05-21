from django.apps import AppConfig


class CoreConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'apps.core'

    def ready(self):
        # Override Django admin to only allow superadmin role or Django superusers.
        # This runs after all apps are loaded, which is the correct place to patch AdminSite.
        from django.contrib import admin

        class SuperAdminSite(admin.AdminSite):
            def has_permission(self, request):
                return (
                    request.user.is_active and (
                        request.user.is_superuser or
                        getattr(request.user, 'role', '') == 'superadmin'
                    )
                )

        # Patch the existing default admin site in-place
        admin.site.__class__ = SuperAdminSite
