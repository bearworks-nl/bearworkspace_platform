import secrets
from django.contrib.auth import login, logout
from django.contrib.auth.decorators import login_required
from django.shortcuts import render, redirect, get_object_or_404
from django.contrib import messages
from django.core.mail import send_mail
from django.conf import settings
from django.utils.decorators import method_decorator
from django.views import View

from .forms import LoginForm, PasswordResetRequestForm, SetNewPasswordForm, ProfileForm
from .models import User, PasswordResetToken


class LoginView(View):
    template_name = "accounts/login.html"

    def get(self, request):
        if request.user.is_authenticated:
            return redirect("core:dashboard")
        return render(request, self.template_name, {"form": LoginForm()})

    def post(self, request):
        form = LoginForm(request, data=request.POST)
        if form.is_valid():
            user = form.get_user()
            login(request, user)
            if not form.cleaned_data.get("remember_me"):
                request.session.set_expiry(0)
            return redirect(request.GET.get("next", "core:dashboard"))
        return render(request, self.template_name, {"form": form})


class LogoutView(View):
    def post(self, request):
        logout(request)
        return redirect("accounts:login")


class PasswordResetRequestView(View):
    template_name = "accounts/password_reset_request.html"

    def get(self, request):
        return render(request, self.template_name, {"form": PasswordResetRequestForm()})

    def post(self, request):
        form = PasswordResetRequestForm(request.POST)
        if form.is_valid():
            email = form.cleaned_data["email"]
            try:
                user = User.objects.get(email=email, is_active=True)
                token_value = secrets.token_urlsafe(48)
                PasswordResetToken.objects.create(user=user, token=token_value)
                reset_url = request.build_absolute_uri(f"/accounts/password-reset/{token_value}/")
                send_mail(
                    subject="Reset your password",
                    message=f"Click the link to reset your password:\n\n{reset_url}\n\nThis link expires in 24 hours.",
                    from_email=settings.DEFAULT_FROM_EMAIL,
                    recipient_list=[email],
                )
            except User.DoesNotExist:
                pass  # Don't reveal whether email exists
            messages.success(request, "If that email exists, a reset link has been sent.")
            return redirect("accounts:login")
        return render(request, self.template_name, {"form": form})


class PasswordResetConfirmView(View):
    template_name = "accounts/password_reset_confirm.html"

    def get_token(self, token_value):
        return get_object_or_404(PasswordResetToken, token=token_value)

    def get(self, request, token):
        reset_token = self.get_token(token)
        if not reset_token.is_valid():
            messages.error(request, "This reset link has expired or already been used.")
            return redirect("accounts:password_reset_request")
        return render(request, self.template_name, {"form": SetNewPasswordForm(), "token": token})

    def post(self, request, token):
        reset_token = self.get_token(token)
        if not reset_token.is_valid():
            messages.error(request, "This reset link has expired or already been used.")
            return redirect("accounts:password_reset_request")
        form = SetNewPasswordForm(request.POST)
        if form.is_valid():
            reset_token.user.set_password(form.cleaned_data["password1"])
            reset_token.user.save()
            reset_token.used = True
            reset_token.save()
            messages.success(request, "Password updated. Please log in.")
            return redirect("accounts:login")
        return render(request, self.template_name, {"form": form, "token": token})


@method_decorator(login_required, name="dispatch")
class ProfileView(View):
    template_name = "accounts/profile.html"

    def get(self, request):
        return render(request, self.template_name, {"form": ProfileForm(instance=request.user)})

    def post(self, request):
        form = ProfileForm(request.POST, request.FILES, instance=request.user)
        if form.is_valid():
            form.save()
            if request.htmx:
                return render(request, "partials/toast.html", {"message": "Profile updated.", "type": "success"})
            messages.success(request, "Profile updated.")
            return redirect("accounts:profile")
        return render(request, self.template_name, {"form": form})
