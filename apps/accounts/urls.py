from django.urls import path
from . import views

app_name = "accounts"

urlpatterns = [
    path("login/", views.LoginView.as_view(), name="login"),
    path("logout/", views.LogoutView.as_view(), name="logout"),
    path("password-reset/", views.PasswordResetRequestView.as_view(), name="password_reset_request"),
    path("password-reset/<str:token>/", views.PasswordResetConfirmView.as_view(), name="password_reset_confirm"),
    path("profile/", views.ProfileView.as_view(), name="profile"),
]
