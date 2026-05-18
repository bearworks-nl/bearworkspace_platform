from django.views import View
from django.shortcuts import render, get_object_or_404, redirect
from django.contrib import messages
from apps.core.middleware import LoginRequiredMixin, CustomerScopedMixin, CustomerAdminRequiredMixin
from apps.billing.models import Plan, Subscription
from .models import ServiceInstance, ServiceType, RecastWorkspaceConfig, Windows365Config, IntuneConfig, IntunePolicy
from .forms import EnableServiceForm, RecastConfigForm, Windows365ConfigForm, IntunePolicyForm


class ServiceListView(CustomerScopedMixin, View):
    def get(self, request):
        filters = self.get_env_filter()
        services = ServiceInstance.objects.filter(**filters).select_related(
            "environment__customer"
        ).order_by("environment__name", "service_type")
        return render(request, "services/list.html", {"services": services})


class ServiceDetailView(CustomerScopedMixin, View):
    def get(self, request, pk):
        service = get_object_or_404(ServiceInstance, pk=pk)
        ctx = {"service": service}
        if service.service_type == ServiceType.WINDOWS_365:
            ctx["cloud_pcs"] = service.windows365_config.cloud_pcs.all() if hasattr(service, "windows365_config") else []
        elif service.service_type == ServiceType.INTUNE:
            ctx["policies"] = service.intune_config.policies.all() if hasattr(service, "intune_config") else []
        try:
            ctx["subscription"] = service.subscription
        except Exception:
            ctx["subscription"] = None
        return render(request, "services/detail.html", ctx)


class EnableServiceView(CustomerAdminRequiredMixin, View):
    def get(self, request):
        from apps.environments.models import Environment
        if request.user.is_superadmin:
            envs = Environment.objects.filter(is_active=True).select_related("customer")
        else:
            envs = Environment.objects.filter(
                customer=request.user.customer, is_active=True
            ).select_related("customer")
        plans = Plan.objects.filter(is_active=True).order_by("service_type", "name")
        return render(request, "services/enable.html", {
            "environments": envs,
            "plans": plans,
            "service_types": ServiceType.choices,
        })

    def post(self, request):
        from apps.environments.models import Environment

        env_id = request.POST.get("environment")
        service_type = request.POST.get("service_type")
        plan_id = request.POST.get("plan")

        if not env_id or not service_type or not plan_id:
            messages.error(request, "Please select an environment, service type, and billing plan.")
            return redirect("services:enable")

        try:
            env = Environment.objects.get(pk=env_id)
        except Environment.DoesNotExist:
            messages.error(request, "Selected environment not found.")
            return redirect("services:enable")

        try:
            plan = Plan.objects.get(pk=plan_id, is_active=True)
        except Plan.DoesNotExist:
            messages.error(request, "Selected plan not found or inactive. Run: python manage.py seed_plans")
            return redirect("services:enable")

        valid_types = [st[0] for st in ServiceType.choices]
        if service_type not in valid_types:
            messages.error(request, "Invalid service type selected.")
            return redirect("services:enable")

        service, created = ServiceInstance.objects.get_or_create(
            environment=env,
            service_type=service_type,
            defaults={"status": ServiceInstance.Status.PROVISIONING},
        )

        if not created:
            messages.warning(request, "This service is already enabled for that environment.")
            return redirect("services:detail", pk=service.pk)

        if service_type == ServiceType.RECAST_WORKSPACE:
            RecastWorkspaceConfig.objects.create(service=service, workspace_url="", api_key="")
        elif service_type == ServiceType.WINDOWS_365:
            Windows365Config.objects.create(service=service)
        elif service_type == ServiceType.INTUNE:
            IntuneConfig.objects.create(service=service)

        Subscription.objects.create(service=service, plan=plan)

        service.status = ServiceInstance.Status.ACTIVE
        service.save(update_fields=["status"])

        messages.success(request, f"{service.get_service_type_display()} enabled for {env.name}.")
        return redirect("services:detail", pk=service.pk)


class PlansForTypeView(LoginRequiredMixin, View):
    """HTMX endpoint — returns filtered plan dropdown for a selected service type."""
    def get(self, request):
        service_type = request.GET.get("service_type", "")
        plans = Plan.objects.filter(is_active=True, service_type=service_type).order_by("name")
        return render(request, "partials/plan_options.html", {"plans": plans})


class DisableServiceView(CustomerAdminRequiredMixin, View):
    def post(self, request, pk):
        service = get_object_or_404(ServiceInstance, pk=pk)
        service.status = ServiceInstance.Status.INACTIVE
        service.save(update_fields=["status"])
        messages.success(request, f"{service.get_service_type_display()} disabled.")
        return redirect("services:detail", pk=service.pk)


# ── Recast ────────────────────────────────────────────────────────────────────

class RecastConfigView(CustomerAdminRequiredMixin, View):
    def get(self, request, pk):
        service = get_object_or_404(ServiceInstance, pk=pk)
        config = getattr(service, "recast_config", None)
        return render(request, "services/recast_config.html", {
            "service": service,
            "form": RecastConfigForm(instance=config),
        })

    def post(self, request, pk):
        service = get_object_or_404(ServiceInstance, pk=pk)
        config = getattr(service, "recast_config", None)
        form = RecastConfigForm(request.POST, instance=config)
        if form.is_valid():
            cfg = form.save(commit=False)
            cfg.service = service
            cfg.save()
            messages.success(request, "Recast configuration saved.")
            return redirect("services:detail", pk=service.pk)
        return render(request, "services/recast_config.html", {"service": service, "form": form})


# ── Windows 365 ───────────────────────────────────────────────────────────────

class Windows365ConfigView(CustomerAdminRequiredMixin, View):
    def get(self, request, pk):
        service = get_object_or_404(ServiceInstance, pk=pk)
        config = getattr(service, "windows365_config", None)
        return render(request, "services/windows365_config.html", {
            "service": service,
            "form": Windows365ConfigForm(instance=config),
        })

    def post(self, request, pk):
        service = get_object_or_404(ServiceInstance, pk=pk)
        config = getattr(service, "windows365_config", None)
        form = Windows365ConfigForm(request.POST, instance=config)
        if form.is_valid():
            cfg = form.save(commit=False)
            cfg.service = service
            cfg.save()
            messages.success(request, "Windows 365 configuration saved.")
            return redirect("services:detail", pk=service.pk)
        return render(request, "services/windows365_config.html", {"service": service, "form": form})


class Windows365SyncView(CustomerAdminRequiredMixin, View):
    def post(self, request, pk):
        service = get_object_or_404(ServiceInstance, pk=pk)
        from .graph_service import sync_cloud_pcs
        try:
            sync_cloud_pcs(service)
            messages.success(request, "Cloud PCs synced from Microsoft Graph.")
        except Exception as e:
            messages.error(request, f"Sync failed: {e}")
        return redirect("services:detail", pk=service.pk)


# ── Intune ────────────────────────────────────────────────────────────────────

class IntuneConfigView(CustomerAdminRequiredMixin, View):
    def get(self, request, pk):
        service = get_object_or_404(ServiceInstance, pk=pk)
        return render(request, "services/intune_config.html", {"service": service})


class IntunePoliciesView(CustomerScopedMixin, View):
    def get(self, request, pk):
        service = get_object_or_404(ServiceInstance, pk=pk)
        policies = service.intune_config.policies.all() if hasattr(service, "intune_config") else []
        return render(request, "services/intune_policies.html", {"service": service, "policies": policies})


class IntunePolicyCreateView(CustomerAdminRequiredMixin, View):
    def get(self, request, pk):
        service = get_object_or_404(ServiceInstance, pk=pk)
        return render(request, "services/intune_policy_form.html", {"service": service, "form": IntunePolicyForm()})

    def post(self, request, pk):
        service = get_object_or_404(ServiceInstance, pk=pk)
        form = IntunePolicyForm(request.POST)
        if form.is_valid():
            policy = form.save(commit=False)
            policy.config = service.intune_config
            policy.save()
            messages.success(request, "Policy created.")
            return redirect("services:intune_policies", pk=pk)
        return render(request, "services/intune_policy_form.html", {"service": service, "form": form})


class IntunePolicyEditView(CustomerAdminRequiredMixin, View):
    def get(self, request, pk, policy_pk):
        service = get_object_or_404(ServiceInstance, pk=pk)
        policy = get_object_or_404(IntunePolicy, pk=policy_pk)
        import json
        initial = {"json_payload": json.dumps(policy.json_payload, indent=2)}
        form = IntunePolicyForm(instance=policy, initial=initial)
        return render(request, "services/intune_policy_form.html", {"service": service, "form": form, "policy": policy})

    def post(self, request, pk, policy_pk):
        service = get_object_or_404(ServiceInstance, pk=pk)
        policy = get_object_or_404(IntunePolicy, pk=policy_pk)
        form = IntunePolicyForm(request.POST, instance=policy)
        if form.is_valid():
            form.save()
            messages.success(request, "Policy updated.")
            return redirect("services:intune_policies", pk=pk)
        return render(request, "services/intune_policy_form.html", {"service": service, "form": form, "policy": policy})


class IntunePolicyDeployView(CustomerAdminRequiredMixin, View):
    def post(self, request, pk, policy_pk):
        service = get_object_or_404(ServiceInstance, pk=pk)
        policy = get_object_or_404(IntunePolicy, pk=policy_pk)
        from .graph_service import deploy_intune_policy
        try:
            deploy_intune_policy(policy)
            messages.success(request, f"Policy '{policy.name}' deployed to Intune.")
        except Exception as e:
            messages.error(request, f"Deploy failed: {e}")
        return redirect("services:intune_policies", pk=pk)
