from django.urls import path
from . import views

app_name = 'services'

urlpatterns = [
    path('', views.service_list, name='list'),
    path('enable/<int:env_pk>/', views.service_enable, name='enable'),
    path('<int:pk>/configure/', views.service_configure, name='configure'),
    path('<int:pk>/toggle/', views.service_toggle, name='toggle'),
    path('<int:pk>/delete/', views.service_delete, name='delete'),
]
