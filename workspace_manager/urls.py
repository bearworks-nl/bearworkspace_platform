from django.contrib import admin
from django.urls import path, include
from django.conf import settings
from django.conf.urls.static import static


urlpatterns = [
    path('admin/', admin.site.urls),
    path('', include('apps.core.urls')),
    path('accounts/', include('apps.accounts.urls')),
    path('users/', include('apps.users.urls')),
    path('environments/', include('apps.environments.urls')),
    path('services/', include('apps.services.urls')),
    path('billing/', include('apps.billing.urls')),
] + static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
