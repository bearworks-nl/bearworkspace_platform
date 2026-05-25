from django.urls import path
from . import views

app_name = 'services'

urlpatterns = [
    path('', views.service_list, name='list'),
    path('reorder/', views.service_reorder, name='reorder'),
    path('enable/<int:env_pk>/', views.service_enable, name='enable'),       # Step 1
    path('<int:pk>/connect/', views.service_connect, name='connect'),         # Step 2
    path('<int:pk>/licenses/', views.service_read_licenses, name='read_licenses'),   # Step 3
    path('<int:pk>/licenses/match/', views.service_match_licenses, name='match_licenses'),  # Step 4
    path('<int:pk>/configure/', views.service_configure, name='configure'),
    path('<int:pk>/toggle/', views.service_toggle, name='toggle'),
    path('<int:pk>/delete/', views.service_delete, name='delete'),
]
