from django.urls import path
from . import views

app_name = "customers"

urlpatterns = [
    path("", views.CustomerListView.as_view(), name="list"),
    path("create/", views.CustomerCreateView.as_view(), name="create"),
    path("<uuid:pk>/", views.CustomerDetailView.as_view(), name="detail"),
    path("<uuid:pk>/edit/", views.CustomerUpdateView.as_view(), name="edit"),
]
