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
    # Member management
    path('<int:pk>/members/add/', views.environment_member_add, name='member_add'),
    path('<int:pk>/members/<int:user_pk>/remove/', views.environment_member_remove, name='member_remove'),
    path('<int:pk>/members/<int:user_pk>/role/', views.environment_member_role, name='member_role'),
]
