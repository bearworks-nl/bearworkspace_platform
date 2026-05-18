from django.shortcuts import render
from apps.core.middleware import LoginRequiredMixin
from django.views import View
from apps.customers.models import Customer
from apps.organisations.models import Organisation
from apps.products.models import ProductInstance
from apps.billing.models import Invoice, Subscription


class DashboardView(LoginRequiredMixin, View):
    def get(self, request):
        user = request.user
        if user.is_superadmin:
            ctx = {
                "total_customers": Customer.objects.count(),
                "total_organisations": Organisation.objects.count(),
                "total_products": ProductInstance.objects.count(),
                "recent_invoices": Invoice.objects.select_related(
                    "subscription__product__organisation__customer"
                ).order_by("-created_at")[:5],
                "active_subscriptions": Subscription.objects.filter(
                    status__in=["active", "trialing"]
                ).count(),
            }
        else:
            customer = user.customer
            ctx = {
                "customer": customer,
                "organisations": Organisation.objects.filter(customer=customer, is_active=True),
                "products": ProductInstance.objects.filter(
                    organisation__customer=customer
                ).select_related("organisation"),
                "recent_invoices": Invoice.objects.filter(
                    subscription__product__organisation__customer=customer
                ).order_by("-created_at")[:5],
            }
        return render(request, "core/dashboard.html", ctx)
