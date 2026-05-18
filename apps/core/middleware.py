from django.shortcuts import redirect
from django.contrib import messages
from functools import wraps


class RBACMiddleware:
    """Attach scoped permission helpers to every request."""

    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        if request.user.is_authenticated:
            request.is_superadmin = request.user.is_superadmin
            request.is_customer_admin = request.user.is_customer_admin
        return self.get_response(request)


# ── View mixins ───────────────────────────────────────────────────────────────

class LoginRequiredMixin:
    def dispatch(self, request, *args, **kwargs):
        if not request.user.is_authenticated:
            return redirect(f"/accounts/login/?next={request.path}")
        return super().dispatch(request, *args, **kwargs)


class SuperAdminRequiredMixin(LoginRequiredMixin):
    def dispatch(self, request, *args, **kwargs):
        result = super().dispatch(request, *args, **kwargs)
        if hasattr(result, "status_code") and result.status_code == 302:
            return result
        if not request.user.is_superadmin:
            messages.error(request, "You do not have permission to access this page.")
            return redirect("core:dashboard")
        return result


class CustomerAdminRequiredMixin(LoginRequiredMixin):
    def dispatch(self, request, *args, **kwargs):
        result = super().dispatch(request, *args, **kwargs)
        if hasattr(result, "status_code") and result.status_code == 302:
            return result
        if not (request.user.is_superadmin or request.user.is_customer_admin):
            messages.error(request, "You do not have permission to access this page.")
            return redirect("core:dashboard")
        return result


class CustomerScopedMixin(LoginRequiredMixin):
    """Restrict queryset to the user's customer unless superadmin."""

    def get_customer_filter(self):
        if self.request.user.is_superadmin:
            return {}
        return {"customer": self.request.user.customer}

    def get_org_filter(self):
        if self.request.user.is_superadmin:
            return {}
        return {"organisation__customer": self.request.user.customer}
