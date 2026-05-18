from django.shortcuts import render
from apps.core.middleware import LoginRequiredMixin
from django.views import View
from apps.customers.models import Customer
from apps.environments.models import Environment
from apps.services.models import ServiceInstance
from apps.billing.models import Invoice, Subscription


class DashboardView(LoginRequiredMixin, View):
    def get(self, request):
        user = request.user
        if user.is_superadmin:
            ctx = {
                "total_customers": Customer.objects.count(),
                "total_environments": Environment.objects.count(),
                "total_services": ServiceInstance.objects.count(),
                "recent_invoices": Invoice.objects.select_related(
                    "subscription__service__environment__customer"
                ).order_by("-created_at")[:5],
                "active_subscriptions": Subscription.objects.filter(
                    status__in=["active", "trialing"]
                ).count(),
            }
        else:
            customer = user.customer
            ctx = {
                "customer": customer,
                "environments": Environment.objects.filter(customer=customer, is_active=True),
                "services": ServiceInstance.objects.filter(
                    environment__customer=customer
                ).select_related("environment"),
                "recent_invoices": Invoice.objects.filter(
                    subscription__service__environment__customer=customer
                ).order_by("-created_at")[:5],
            }
        return render(request, "core/dashboard.html", ctx)
