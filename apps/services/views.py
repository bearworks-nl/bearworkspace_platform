from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django import forms
from apps.environments.models import Environment
from .models import Service, RecastConfig, Windows365Config, IntuneConfig, SERVICE_TYPE_CHOICES


# ---------------------------------------------------------------------------
# Forms
# ---------------------------------------------------------------------------

class ServiceEnableForm(forms.Form):
    service_type = forms.ChoiceField(
        choices=SERVICE_TYPE_CHOICES,
        widget=forms.Select(attrs={'class': 'form-input'})
    )
    name = forms.CharField(
        max_length=200,
        required=False,
        widget=forms.TextInput(attrs={
            'class': 'form-input',
            'placeholder': 'e.g. Production Recast, Client A W365 …'
        }),
        help_text='Optional. If left blank the service type name is used.'
    )


class ServiceNameForm(forms.ModelForm):
    class Meta:
        model = Service
        fields = ('name',)
        widgets = {
            'name': forms.TextInput(attrs={'class': 'form-input', 'placeholder': 'e.g. Production Recast'})
        }


class RecastConfigForm(forms.ModelForm):
    class Meta:
        model = RecastConfig
        fields = ('api_url', 'api_key')
        widgets = {
            'api_url': forms.URLInput(attrs={'class': 'form-input'}),
            'api_key': forms.TextInput(attrs={'class': 'form-input'}),
        }


class Windows365ConfigForm(forms.ModelForm):
    class Meta:
        model = Windows365Config
        fields = ('application_id', 'tenant_id', 'client_secret')
        widgets = {f: forms.TextInput(attrs={'class': 'form-input'})
                   for f in ['application_id', 'tenant_id', 'client_secret']}


class IntuneConfigForm(forms.ModelForm):
    class Meta:
        model = IntuneConfig
        fields = ('application_id', 'tenant_id', 'client_secret')
        widgets = {f: forms.TextInput(attrs={'class': 'form-input'})
                   for f in ['application_id', 'tenant_id', 'client_secret']}


# ---------------------------------------------------------------------------
# Step 1 + generic list
# ---------------------------------------------------------------------------

@login_required
def service_list(request):
    environments = Environment.objects.filter(owner=request.user)
    selected_env_id = request.GET.get('env')
    selected_env = None

    if selected_env_id:
        selected_env = get_object_or_404(Environment, pk=selected_env_id, owner=request.user)
        services = Service.objects.filter(environment=selected_env).select_related('environment')
    else:
        services = Service.objects.filter(environment__owner=request.user).select_related('environment')

    return render(request, 'services/list.html', {
        'environments': environments,
        'selected_env': selected_env,
        'services': services,
    })


@login_required
def service_enable(request, env_pk):
    """Step 1 – Add a new service (picks type + optional name)."""
    env = get_object_or_404(Environment, pk=env_pk, owner=request.user)
    if request.method == 'POST':
        form = ServiceEnableForm(request.POST)
        if form.is_valid():
            stype = form.cleaned_data['service_type']
            name = form.cleaned_data.get('name', '').strip()
            service = Service.objects.create(
                environment=env,
                service_type=stype,
                name=name,
                enabled=True,
            )
            messages.success(request, f'Service "{service.display_name}" added. Now connect it below.')
            # Immediately send to Step 2
            return redirect('services:connect', pk=service.pk)
    else:
        form = ServiceEnableForm()
    return render(request, 'services/enable.html', {'form': form, 'environment': env})


# ---------------------------------------------------------------------------
# Step 2 – Connect service
# ---------------------------------------------------------------------------

@login_required
def service_connect(request, pk):
    """
    Step 2 – Connect the service.

    For Recast services: checks whether a RecastConfig with valid credentials
    already exists (i.e. the service is 'available').
      - Yes  → marks is_connected=True, redirects to read_licenses (Step 3)
      - No   → renders connect.html offering to configure credentials or order
    """
    service = get_object_or_404(Service, pk=pk, environment__owner=request.user)

    if service.service_type != 'recast_workspace':
        # Non-Recast services go straight to configure
        return redirect('services:configure', pk=service.pk)

    config = getattr(service, 'recast_config', None)
    already_available = config is not None and bool(config.api_url) and bool(config.api_key)

    if request.method == 'POST':
        action = request.POST.get('action')

        if action == 'connect' and already_available:
            service.is_connected = True
            service.status = 'active'
            service.save()
            messages.success(request, 'Service connected. Reading licenses…')
            return redirect('services:read_licenses', pk=service.pk)

        elif action == 'order':
            # Placeholder: redirect to the (TBD) order flow
            messages.info(request, 'The order flow is not yet available. Please check back later.')
            return redirect('services:connect', pk=service.pk)

    return render(request, 'services/connect.html', {
        'service': service,
        'already_available': already_available,
        'config': config,
    })


# ---------------------------------------------------------------------------
# Step 3 – Read licenses
# ---------------------------------------------------------------------------

@login_required
def service_read_licenses(request, pk):
    """
    Step 3 – Read available licenses from the Recast API.

    In production this would call the Recast API and populate
    config.license_count / config.license_numbers.
    For now it uses whatever is already stored, and a POST with
    action='sync' simulates fetching (stub).
    """
    service = get_object_or_404(Service, pk=pk, environment__owner=request.user)

    if service.service_type != 'recast_workspace':
        return redirect('services:configure', pk=service.pk)

    config, _ = RecastConfig.objects.get_or_create(service=service)

    if request.method == 'POST' and request.POST.get('action') == 'sync':
        # --- Replace this stub with a real Recast API call ---
        # e.g.: licenses = recast_client.get_licenses(config.api_url, config.api_key)
        # config.license_count = len(licenses)
        # config.license_numbers = [lic['id'] for lic in licenses]
        # config.save()
        messages.info(request, 'License sync is not yet wired to the Recast API. Stub ran.')
        return redirect('services:read_licenses', pk=service.pk)

    return render(request, 'services/read_licenses.html', {
        'service': service,
        'config': config,
    })


# ---------------------------------------------------------------------------
# Step 4 – Match licenses against orders
# ---------------------------------------------------------------------------

@login_required
def service_match_licenses(request, pk):
    """
    Step 4 – Match license numbers against existing orders/subscriptions.

    Looks for Subscriptions whose plan.name contains any of the license
    numbers stored in config.license_numbers.  A real implementation would
    compare against an Order model (TBD).
    """
    from apps.billing.models import Subscription

    service = get_object_or_404(Service, pk=pk, environment__owner=request.user)

    if service.service_type != 'recast_workspace':
        return redirect('services:configure', pk=service.pk)

    config = getattr(service, 'recast_config', None)
    license_numbers = config.license_numbers if config else []

    # --- Replace with proper Order model lookup when available ---
    matched_subscriptions = []
    if license_numbers:
        matched_subscriptions = list(
            Subscription.objects.filter(
                service=service,
                user=request.user,
            ).select_related('plan')
        )

    no_licenses = not license_numbers

    if request.method == 'POST':
        action = request.POST.get('action')
        if action == 'order_new':
            messages.info(request, 'Redirecting to order new licenses… (TBD)')
            return redirect('billing:plan_list')
        elif action == 'add_licenses':
            messages.info(request, 'Redirecting to add additional licenses… (TBD)')
            return redirect('billing:plan_list')

    return render(request, 'services/match_licenses.html', {
        'service': service,
        'config': config,
        'license_numbers': license_numbers,
        'matched_subscriptions': matched_subscriptions,
        'no_licenses': no_licenses,
    })


# ---------------------------------------------------------------------------
# Standard configure / delete views (unchanged)
# ---------------------------------------------------------------------------

@login_required
def service_configure(request, pk):
    service = get_object_or_404(Service, pk=pk, environment__owner=request.user)
    config_obj = None
    FormClass = None

    if service.service_type == 'recast_workspace':
        config_obj, _ = RecastConfig.objects.get_or_create(service=service)
        FormClass = RecastConfigForm
    elif service.service_type == 'windows_365':
        config_obj, _ = Windows365Config.objects.get_or_create(
            service=service, defaults={'application_id': '', 'tenant_id': ''})
        FormClass = Windows365ConfigForm
    elif service.service_type == 'intune':
        config_obj, _ = IntuneConfig.objects.get_or_create(
            service=service, defaults={'application_id': '', 'tenant_id': ''})
        FormClass = IntuneConfigForm

    from apps.billing.models import Plan, Subscription
    available_plans = Plan.objects.filter(service=service, is_active=True)
    active_subscription = Subscription.objects.filter(
        service=service, user=request.user
    ).exclude(status='canceled').first()

    if request.method == 'POST':
        name_form = ServiceNameForm(request.POST, instance=service)
        config_form = FormClass(request.POST, instance=config_obj) if config_obj else None

        name_valid = name_form.is_valid()
        config_valid = config_form.is_valid() if config_form else True

        if name_valid and config_valid:
            name_form.save()
            if config_form:
                config_form.save()
            service.status = 'active'
            service.save()

            plan_id = request.POST.get('plan_id')
            if plan_id and not active_subscription:
                try:
                    plan = Plan.objects.get(pk=plan_id, service=service)
                    Subscription.objects.create(
                        user=request.user,
                        service=service,
                        plan=plan,
                        status='trialing',
                    )
                    messages.success(request, f'Service configured and subscribed to "{plan.name}".')
                except Plan.DoesNotExist:
                    messages.warning(request, 'Service configured, but selected plan was not found.')
            else:
                messages.success(request, 'Service configured successfully.')

            # After configuring a Recast service, send to Step 2
            if service.service_type == 'recast_workspace':
                return redirect('services:connect', pk=service.pk)
            return redirect('environments:detail', pk=service.environment.pk)
    else:
        name_form = ServiceNameForm(instance=service)
        config_form = FormClass(instance=config_obj) if config_obj else None

    return render(request, 'services/configure.html', {
        'service': service,
        'name_form': name_form,
        'config_form': config_form,
        'available_plans': available_plans,
        'active_subscription': active_subscription,
    })


@login_required
def service_toggle(request, pk):
    service = get_object_or_404(Service, pk=pk, environment__owner=request.user)
    if request.method == 'POST':
        service.enabled = not service.enabled
        service.save()
        messages.success(request, f'Service {"enabled" if service.enabled else "disabled"}.')
    return redirect('environments:detail', pk=service.environment.pk)


@login_required
def service_delete(request, pk):
    service = get_object_or_404(Service, pk=pk, environment__owner=request.user)
    env_pk = service.environment.pk
    if request.method == 'POST':
        service.delete()
        messages.success(request, 'Service removed.')
        return redirect('environments:detail', pk=env_pk)
    # GET: show confirmation page
    return render(request, 'services/confirm_delete.html', {
        'service': service,
        'cancel_url': service.environment.pk,
    })
