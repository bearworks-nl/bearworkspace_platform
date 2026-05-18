from django.views import View
from django.shortcuts import render, get_object_or_404, redirect
from django.contrib import messages
from apps.core.middleware import LoginRequiredMixin, CustomerScopedMixin, CustomerAdminRequiredMixin
from apps.billing.models import Plan, Subscription
from .models import ProductInstance, ProductType, RecastWorkspaceConfig, Windows365Config, IntuneConfig, IntunePolicy
from .forms import EnableProductForm, RecastConfigForm, Windows365ConfigForm, IntunePolicyForm


class ProductListView(CustomerScopedMixin, View):
    def get(self, request):
        filters = self.get_org_filter()
        products = ProductInstance.objects.filter(**filters).select_related(
            "organisation__customer"
        ).order_by("organisation__name", "product_type")
        return render(request, "products/list.html", {"products": products})


class ProductDetailView(CustomerScopedMixin, View):
    def get(self, request, pk):
        product = get_object_or_404(ProductInstance, pk=pk)
        ctx = {"product": product}
        if product.product_type == ProductType.WINDOWS_365:
            ctx["cloud_pcs"] = product.windows365_config.cloud_pcs.all() if hasattr(product, "windows365_config") else []
        elif product.product_type == ProductType.INTUNE:
            ctx["policies"] = product.intune_config.policies.all() if hasattr(product, "intune_config") else []
        try:
            ctx["subscription"] = product.subscription
        except Exception:
            ctx["subscription"] = None
        return render(request, "products/detail.html", ctx)


class EnableProductView(CustomerAdminRequiredMixin, View):
    def get(self, request):
        from apps.organisations.models import Organisation
        if request.user.is_superadmin:
            orgs = Organisation.objects.filter(is_active=True).select_related("customer")
        else:
            orgs = Organisation.objects.filter(
                customer=request.user.customer, is_active=True
            ).select_related("customer")
        # Show all active plans on initial load; filtered by HTMX on product type change
        plans = Plan.objects.filter(is_active=True).order_by("product_type", "name")
        return render(request, "products/enable.html", {
            "organisations": orgs,
            "plans": plans,
            "product_types": ProductType.choices,
        })

    def post(self, request):
        from apps.organisations.models import Organisation

        org_id = request.POST.get("organisation")
        product_type = request.POST.get("product_type")
        plan_id = request.POST.get("plan")

        # Validate all fields present
        if not org_id or not product_type or not plan_id:
            messages.error(request, "Please select an organisation, product type, and billing plan.")
            return redirect("products:enable")

        # Safe lookups with friendly errors
        try:
            org = Organisation.objects.get(pk=org_id)
        except Organisation.DoesNotExist:
            messages.error(request, "Selected organisation not found.")
            return redirect("products:enable")

        try:
            plan = Plan.objects.get(pk=plan_id, is_active=True)
        except Plan.DoesNotExist:
            messages.error(request, "Selected plan not found or inactive. Run: python manage.py seed_plans")
            return redirect("products:enable")

        # Validate product type value
        valid_types = [pt[0] for pt in ProductType.choices]
        if product_type not in valid_types:
            messages.error(request, "Invalid product type selected.")
            return redirect("products:enable")

        product, created = ProductInstance.objects.get_or_create(
            organisation=org,
            product_type=product_type,
            defaults={"status": ProductInstance.Status.PROVISIONING},
        )

        if not created:
            messages.warning(request, "This product is already enabled for that organisation.")
            return redirect("products:detail", pk=product.pk)

        # Create product-specific config
        if product_type == ProductType.RECAST_WORKSPACE:
            RecastWorkspaceConfig.objects.create(product=product, workspace_url="", api_key="")
        elif product_type == ProductType.WINDOWS_365:
            Windows365Config.objects.create(product=product)
        elif product_type == ProductType.INTUNE:
            IntuneConfig.objects.create(product=product)

        # Create subscription
        Subscription.objects.create(product=product, plan=plan)

        product.status = ProductInstance.Status.ACTIVE
        product.save(update_fields=["status"])

        messages.success(request, f"{product.get_product_type_display()} enabled for {org.name}.")
        return redirect("products:detail", pk=product.pk)


class PlansForTypeView(LoginRequiredMixin, View):
    """HTMX endpoint — returns filtered plan dropdown for a selected product type."""
    def get(self, request):
        product_type = request.GET.get("product_type", "").strip()
        if product_type:
            plans = Plan.objects.filter(
                is_active=True,
                product_type=product_type
            ).order_by("name")
        else:
            plans = Plan.objects.none()
        return render(request, "partials/plan_options.html", {
            "plans": plans,
            "selected_type": product_type,
        })


class DisableProductView(CustomerAdminRequiredMixin, View):
    def post(self, request, pk):
        product = get_object_or_404(ProductInstance, pk=pk)
        product.status = ProductInstance.Status.INACTIVE
        product.save(update_fields=["status"])
        try:
            sub = product.subscription
            from apps.billing.mollie_service import cancel_mollie_subscription
            cancel_mollie_subscription(product.organisation.customer, sub)
            sub.status = "cancelled"
            sub.save(update_fields=["status"])
        except Exception:
            pass
        messages.success(request, f"{product.get_product_type_display()} disabled.")
        return redirect("products:list")


# ── Recast ────────────────────────────────────────────────────────────────────

class RecastConfigView(CustomerAdminRequiredMixin, View):
    def get(self, request, pk):
        product = get_object_or_404(ProductInstance, pk=pk, product_type=ProductType.RECAST_WORKSPACE)
        cfg, _ = RecastWorkspaceConfig.objects.get_or_create(
            product=product, defaults={"workspace_url": "", "api_key": ""}
        )
        return render(request, "products/recast_config.html", {"product": product, "form": RecastConfigForm(instance=cfg)})

    def post(self, request, pk):
        product = get_object_or_404(ProductInstance, pk=pk, product_type=ProductType.RECAST_WORKSPACE)
        cfg = product.recast_config
        form = RecastConfigForm(request.POST, instance=cfg)
        if form.is_valid():
            form.save()
            if request.htmx:
                return render(request, "partials/toast.html", {"message": "Config saved.", "type": "success"})
            messages.success(request, "Recast config saved.")
            return redirect("products:detail", pk=pk)
        return render(request, "products/recast_config.html", {"product": product, "form": form})


# ── Windows 365 ───────────────────────────────────────────────────────────────

class Windows365ConfigView(CustomerAdminRequiredMixin, View):
    def get(self, request, pk):
        product = get_object_or_404(ProductInstance, pk=pk, product_type=ProductType.WINDOWS_365)
        cfg, _ = Windows365Config.objects.get_or_create(product=product)
        return render(request, "products/windows365_config.html", {"product": product, "form": Windows365ConfigForm(instance=cfg)})

    def post(self, request, pk):
        product = get_object_or_404(ProductInstance, pk=pk, product_type=ProductType.WINDOWS_365)
        cfg = product.windows365_config
        form = Windows365ConfigForm(request.POST, instance=cfg)
        if form.is_valid():
            form.save()
            messages.success(request, "Windows 365 config saved.")
            return redirect("products:detail", pk=pk)
        return render(request, "products/windows365_config.html", {"product": product, "form": form})


class Windows365SyncView(CustomerAdminRequiredMixin, View):
    def post(self, request, pk):
        product = get_object_or_404(ProductInstance, pk=pk, product_type=ProductType.WINDOWS_365)
        from .graph_service import sync_cloud_pcs
        try:
            count = sync_cloud_pcs(product)
            messages.success(request, f"Synced {count} Cloud PCs.")
        except Exception as e:
            messages.error(request, f"Sync failed: {e}")
        return redirect("products:detail", pk=pk)


# ── Intune ────────────────────────────────────────────────────────────────────

class IntuneConfigView(CustomerAdminRequiredMixin, View):
    def get(self, request, pk):
        product = get_object_or_404(ProductInstance, pk=pk, product_type=ProductType.INTUNE)
        return render(request, "products/intune_config.html", {"product": product})


class IntunePoliciesView(CustomerScopedMixin, View):
    def get(self, request, pk):
        product = get_object_or_404(ProductInstance, pk=pk, product_type=ProductType.INTUNE)
        policies = product.intune_config.policies.all()
        return render(request, "products/intune_policies.html", {"product": product, "policies": policies})


class IntunePolicyCreateView(CustomerAdminRequiredMixin, View):
    def get(self, request, pk):
        product = get_object_or_404(ProductInstance, pk=pk, product_type=ProductType.INTUNE)
        return render(request, "products/intune_policy_form.html", {"product": product, "form": IntunePolicyForm()})

    def post(self, request, pk):
        product = get_object_or_404(ProductInstance, pk=pk, product_type=ProductType.INTUNE)
        form = IntunePolicyForm(request.POST)
        if form.is_valid():
            policy = form.save(commit=False)
            policy.config = product.intune_config
            policy.save()
            messages.success(request, f"Policy '{policy.name}' created.")
            return redirect("products:intune_policies", pk=pk)
        return render(request, "products/intune_policy_form.html", {"product": product, "form": form})


class IntunePolicyEditView(CustomerAdminRequiredMixin, View):
    def get(self, request, pk, policy_pk):
        product = get_object_or_404(ProductInstance, pk=pk)
        policy = get_object_or_404(IntunePolicy, pk=policy_pk)
        import json
        initial = {"json_payload": json.dumps(policy.json_payload, indent=2)}
        form = IntunePolicyForm(instance=policy, initial=initial)
        return render(request, "products/intune_policy_form.html", {"product": product, "form": form, "policy": policy})

    def post(self, request, pk, policy_pk):
        product = get_object_or_404(ProductInstance, pk=pk)
        policy = get_object_or_404(IntunePolicy, pk=policy_pk)
        form = IntunePolicyForm(request.POST, instance=policy)
        if form.is_valid():
            form.save()
            messages.success(request, "Policy updated.")
            return redirect("products:intune_policies", pk=pk)
        return render(request, "products/intune_policy_form.html", {"product": product, "form": form, "policy": policy})


class IntunePolicyDeployView(CustomerAdminRequiredMixin, View):
    def post(self, request, pk, policy_pk):
        product = get_object_or_404(ProductInstance, pk=pk)
        policy = get_object_or_404(IntunePolicy, pk=policy_pk)
        from .graph_service import deploy_intune_policy
        try:
            deploy_intune_policy(policy)
            messages.success(request, f"Policy '{policy.name}' deployed to Intune.")
        except Exception as e:
            messages.error(request, f"Deploy failed: {e}")
        return redirect("products:intune_policies", pk=pk)