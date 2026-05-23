from django.urls import path
from . import views

app_name = 'environments'

urlpatterns = [
    path('', views.environment_list, name='list'),
    path('reorder/', views.environment_reorder, name='reorder'),
    path('create/', views.environment_create, name='create'),
    path('<int:pk>/', views.environment_detail, name='detail'),
    path('<int:pk>/edit/', views.environment_edit, name='edit'),
    path('<int:pk>/delete/', views.environment_delete, name='delete'),
]
