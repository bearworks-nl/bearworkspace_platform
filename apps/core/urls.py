from django.urls import path
from django.views.generic import RedirectView
from . import views

app_name = "core"

urlpatterns = [
    path("", RedirectView.as_view(pattern_name="core:dashboard"), name="home"),
    path("dashboard/", views.DashboardView.as_view(), name="dashboard"),
]
