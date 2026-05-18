from django.views import View
from django.views.decorators.csrf import csrf_exempt
from django.utils.decorators import method_decorator
from django.shortcuts import render, get_object_or_404, redirect
from django.http import HttpResponse
from django.contrib import messages
from apps.core.middleware import LoginRequiredMixin, CustomerScopedMixin, SuperAdminRequiredMixin
from .models import Invoice, Subscription, Plan
from .forms import PlanForm, SubscriptionPlanChangeForm
import logging

logger = logging.getLogger(__name__)


# ── Plans ─────────────────────────────────────────────────────────────────────

class PlanListView(SuperAdminRequiredMixin, View):
    def get(self, request):
        plans = Plan.objects.all().order_by("product_type", "name")
        # Group by product type for display
        from apps.products.models import ProductType
        grouped = {}
        for pt_value, pt_label in ProductType.choices:
            grouped[pt_label] = plans.filter(product_type=pt_value)
        return render(request, "billing/plan_list.html", {
            "plans": plans,
            "grouped": grouped,
        })


class PlanCreateView(SuperAdminRequiredMixin, View):
    def get(self, request):
        return render(request, "billing/plan_form.html", {"form": PlanForm()})

    def post(self, request):
        form = PlanForm(request.POST)
        if form.is_valid():
            plan = form.save()
            messages.success(request, f"Plan '{plan.name}' created.")
            return redirect("billing:plan_list")
        return render(request, "billing/plan_form.html", {"form": form})


class PlanUpdateView(SuperAdminRequiredMixin, View):
    def get(self, request, pk):
        plan = get_object_or_404(Plan, pk=pk)
        return render(request, "billing/plan_form.html", {"form": PlanForm(instance=plan), "plan": plan})

    def post(self, request, pk):
        plan = get_object_or_404(Plan, pk=pk)
        form = PlanForm(request.POST, instance=plan)
        if form.is_valid():
            form.save()
            if request.htmx:
                return render(request, "partials/toast.html", {"message": "Plan saved.", "type": "success"})
            messages.success(request, f"Plan '{plan.name}' updated.")
            return redirect("billing:plan_list")
        return render(request, "billing/plan_form.html", {"form": form, "plan": plan})


class PlanToggleView(SuperAdminRequiredMixin, View):
    def post(self, request, pk):
        plan = get_object_or_404(Plan, pk=pk)
        plan.is_active = not plan.is_active
        plan.save(update_fields=["is_active"])
        status = "activated" if plan.is_active else "deactivated"
        messages.success(request, f"Plan '{plan.name}' {status}.")
        return redirect("billing:plan_list")


# ── Subscriptions ─────────────────────────────────────────────────────────────

class SubscriptionListView(CustomerScopedMixin, View):
    def get(self, request):
        filters = self.get_org_filter()
        subscriptions = Subscription.objects.filter(
            **{k.replace("organisation__", "product__organisation__"): v for k, v in filters.items()}
        ).select_related("plan", "product__organisation__customer").order_by("-created_at")
        return render(request, "billing/subscription_list.html", {"subscriptions": subscriptions})


class SubscriptionDetailView(CustomerScopedMixin, View):
    def get(self, request, pk):
        sub = get_object_or_404(Subscription, pk=pk)
        invoices = sub.invoices.order_by("-created_at")
        snapshots = sub.usage_snapshots.order_by("-period_start")[:6]
        return render(request, "billing/subscription_detail.html", {
            "subscription": sub,
            "invoices": invoices,
            "snapshots": snapshots,
        })


class SubscriptionEditView(SuperAdminRequiredMixin, View):
    def get(self, request, pk):
        sub = get_object_or_404(Subscription, pk=pk)
        return render(request, "billing/subscription_edit.html", {
            "subscription": sub,
            "form": SubscriptionPlanChangeForm(instance=sub),
        })

    def post(self, request, pk):
        sub = get_object_or_404(Subscription, pk=pk)
        form = SubscriptionPlanChangeForm(request.POST, instance=sub)
        if form.is_valid():
            form.save()
            messages.success(request, "Subscription updated.")
            return redirect("billing:subscription_detail", pk=pk)
        return render(request, "billing/subscription_edit.html", {"subscription": sub, "form": form})


# ── Invoices ──────────────────────────────────────────────────────────────────

class InvoiceListView(CustomerScopedMixin, View):
    def get(self, request):
        filters = self.get_org_filter()
        invoices = Invoice.objects.filter(
            **{k.replace("organisation__", "subscription__product__organisation__"): v
               for k, v in filters.items()}
        ).select_related(
            "subscription__product__organisation__customer", "subscription__plan"
        ).order_by("-created_at")
        return render(request, "billing/invoice_list.html", {"invoices": invoices})


class InvoiceDetailView(CustomerScopedMixin, View):
    def get(self, request, pk):
        invoice = get_object_or_404(Invoice, pk=pk)
        return render(request, "billing/invoice_detail.html", {"invoice": invoice})


class InvoiceDownloadView(CustomerScopedMixin, View):
    def get(self, request, pk):
        invoice = get_object_or_404(Invoice, pk=pk)
        if not invoice.pdf:
            from .tasks import generate_invoice_pdf
            generate_invoice_pdf.delay(str(invoice.id))
            messages.info(request, "PDF is being generated, please try again shortly.")
            return redirect("billing:invoice_detail", pk=pk)
        return HttpResponse(
            invoice.pdf.read(),
            content_type="application/pdf",
            headers={"Content-Disposition": f'attachment; filename="{invoice.invoice_number}.pdf"'},
        )


# ── Mollie ────────────────────────────────────────────────────────────────────

@method_decorator(csrf_exempt, name="dispatch")
class MollieWebhookView(View):
    def post(self, request):
        payment_id = request.POST.get("id")
        if not payment_id:
            return HttpResponse(status=400)
        try:
            from .mollie_service import handle_webhook
            handle_webhook(payment_id)
        except Exception as e:
            logger.error("Webhook processing error: %s", e)
            return HttpResponse(status=500)
        return HttpResponse(status=200)


class SetupMandateView(LoginRequiredMixin, View):
    def get(self, request, subscription_pk):
        sub = get_object_or_404(Subscription, pk=subscription_pk)
        customer = sub.product.organisation.customer
        from .mollie_service import create_first_payment
        redirect_url = request.build_absolute_uri(f"/billing/subscriptions/{sub.pk}/")
        checkout_url = create_first_payment(customer, sub, redirect_url)
        return redirect(checkout_url)
