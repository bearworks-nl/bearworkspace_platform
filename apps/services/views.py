import json
from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.http import JsonResponse
from django.views.decorators.http import require_POST
from django import forms

from apps.environments.models import Environment
from .models import (
    Service, RecastConfig, Windows365Config, IntuneConfig,
    SERVICE_TYPE_CHOICES,
)


# ---------------------------------------------------------------------------
# Forms
# ---------------------------------------------------------------------------

class ServiceEnableForm(forms.Form):
    service_type = forms.ChoiceField(
        choices=[],
        widget=forms.Select(attrs={'class': 'form-input'}),
    )
    name = forms.CharField(
        required=False,
        max_length=200,
        widget=forms.TextInput(attrs={
            'class': 'form-input',
            'placeholder': 'e.g. Production Recast, Client A W365 …'
        }),
        help_text='Optional. If left blank the service type name is used.'
    )

    def __init__(self, *args, available_choices=None, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['service_type'].choices = available_choices or SERVICE_TYPE_CHOICES


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
        services = (
            Service.objects
            .filter(environment=selected_env)
            .select_related('environment')
            .order_by('sort_order', 'service_type', 'name')
        )
    else:
        services = (
            Service.objects
            .filter(environment__owner=request.user)
            .select_related('environment')
            .order_by('sort_order', 'environment', 'service_type', 'name')
        )

    return render(request, 'services/list.html', {
        'environments': environments,
        'selected_env': selected_env,
        'services': services,
    })


@login_required
@require_POST
def service_reorder(request):
    """
    Accepts a JSON body: {"order": [3, 1, 5, 2, ...]}
    (a list of service PKs in the new desired order).
    Updates sort_order for each service owned by this user.
    """
    try:
        data = json.loads(request.body)
        order = data.get('order', [])
    except (json.JSONDecodeError, AttributeError):
        return JsonResponse({'error': 'Invalid JSON'}, status=400)

    # Only allow updating services this user owns
    owned_ids = set(
        Service.objects
        .filter(environment__owner=request.user)
        .values_list('pk', flat=True)
    )

    for position, pk in enumerate(order):
        pk = int(pk)
        if pk in owned_ids:
            Service.objects.filter(pk=pk).update(sort_order=position)

    return JsonResponse({'status': 'ok'})


@login_required
def service_enable(request, env_pk):
    """Step 1 – Add a new service (picks type + optional name)."""
    env = get_object_or_404(Environment, pk=env_pk, owner=request.user)

    existing_types = set(
        Service.objects.filter(environment=env).values_list('service_type', flat=True)
    )
    available_choices = [
        (value, label) for value, label in SERVICE_TYPE_CHOICES
        if value not in existing_types
    ]

    if not available_choices:
        messages.info(request, 'All available services have already been added to this environment.')
        return redirect('environments:detail', pk=env_pk)

    if request.method == 'POST':
        form = ServiceEnableForm(request.POST, available_choices=available_choices)
        if form.is_valid():
            stype = form.cleaned_data['service_type']
            name = form.cleaned_data.get('name', '').strip()
            if Service.objects.filter(environment=env, service_type=stype).exists():
                messages.error(request, 'That service type has already been added to this environment.')
                return redirect('services:enable', env_pk=env_pk)
            # Place new services at the end of the current list
            max_order = Service.objects.filter(environment__owner=request.user).count()
            service = Service.objects.create(
                environment=env,
                service_type=stype,
                name=name,
                enabled=True,
                sort_order=max_order,
            )
            messages.success(request, f'Service "{service.display_name}" added. Now connect it below.')
            return redirect('services:connect', pk=service.pk)
    else:
        form = ServiceEnableForm(available_choices=available_choices)
    return render(request, 'services/enable.html', {'form': form, 'environment': env})


# ---------------------------------------------------------------------------
# Step 2 – Connect service
# ---------------------------------------------------------------------------

@login_required
def service_connect(request, pk):
    service = get_object_or_404(Service, pk=pk, environment__owner=request.user)

    if service.service_type != 'recast_workspace':
        return redirect('services:configure', pk=service.pk)

    config = getattr(service, 'recast_config', None)
    already_available = config is not None and bool(config.api_url) and bool(config.api_key)

    if request.method == 'POST':
        action = request.POST.get('action')

        if action == 'connect' and already_available:
            service.is_connected = True
            service.status = 'active'
            service.save()
            messages.success(request, 'Service connected.')
            return redirect('services:read_licenses', pk=service.pk)

        elif action == 'configure':
            return redirect('services:configure', pk=service.pk)

        elif action == 'order':
            messages.info(request, 'Redirecting to order a Recast licence… (TBD)')
            return redirect('billing:plan_list')

    return render(request, 'services/connect.html', {
        'service': service,
        'config': config,
        'already_available': already_available,
    })


# ---------------------------------------------------------------------------
# Step 3 – Read licences from Recast API
# ---------------------------------------------------------------------------

@login_required
def service_read_licenses(request, pk):
    service = get_object_or_404(Service, pk=pk, environment__owner=request.user)

    if service.service_type != 'recast_workspace':
        return redirect('services:configure', pk=service.pk)

    config = getattr(service, 'recast_config', None)

    if request.method == 'POST':
        action = request.POST.get('action')
        if action == 'read' and config:
            # Placeholder: in production, call the Recast API here
            config.license_count = 0
            config.license_numbers = []
            config.save()
            messages.success(request, 'Licence data refreshed.')
            return redirect('services:match_licenses', pk=service.pk)

    return render(request, 'services/read_licenses.html', {
        'service': service,
        'config': config,
    })


# ---------------------------------------------------------------------------
# Step 4 – Match licences to an order
# ---------------------------------------------------------------------------

@login_required
def service_match_licenses(request, pk):
    from apps.billing.models import Subscription

    service = get_object_or_404(Service, pk=pk, environment__owner=request.user)

    if service.service_type != 'recast_workspace':
        return redirect('services:configure', pk=service.pk)

    config = getattr(service, 'recast_config', None)
    license_numbers = config.license_numbers if config else []

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
# Standard configure / delete views
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
    return render(request, 'services/confirm_delete.html', {
        'service': service,
        'cancel_url': service.environment.pk,
    })
