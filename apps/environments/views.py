import json
from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.http import JsonResponse
from django.utils.text import slugify
from django.views.decorators.http import require_POST
from django import forms
from apps.accounts.models import User
from .models import Environment, EnvironmentMembership


class EnvironmentForm(forms.ModelForm):
    class Meta:
        model = Environment
        fields = ('name', 'description', 'azure_tenant_id', 'status')
        widgets = {
            'name': forms.TextInput(attrs={'class': 'form-input'}),
            'description': forms.Textarea(attrs={'class': 'form-input', 'rows': 3}),
            'azure_tenant_id': forms.TextInput(attrs={'class': 'form-input'}),
            'status': forms.Select(attrs={'class': 'form-input'}),
        }


@login_required
def environment_list(request):
    envs = Environment.objects.filter(owner=request.user)
    return render(request, 'environments/list.html', {'environments': envs})


@login_required
@require_POST
def environment_reorder(request):
    try:
        data = json.loads(request.body)
        order = data.get('order', [])
    except (json.JSONDecodeError, AttributeError):
        return JsonResponse({'error': 'Invalid JSON'}, status=400)

    owned_ids = set(
        Environment.objects.filter(owner=request.user).values_list('pk', flat=True)
    )
    for position, pk in enumerate(order):
        pk = int(pk)
        if pk in owned_ids:
            Environment.objects.filter(pk=pk, owner=request.user).update(sort_order=position)

    return JsonResponse({'status': 'ok'})


@login_required
def environment_create(request):
    if request.method == 'POST':
        form = EnvironmentForm(request.POST)
        if form.is_valid():
            env = form.save(commit=False)
            env.owner = request.user
            base_slug = slugify(env.name)
            slug = base_slug
            i = 1
            while Environment.objects.filter(slug=slug).exists():
                slug = f'{base_slug}-{i}'
                i += 1
            env.slug = slug
            max_order = Environment.objects.filter(owner=request.user).count()
            env.sort_order = max_order
            env.save()
            messages.success(request, f'Environment "{env.name}" created.')
            return redirect('environments:detail', pk=env.pk)
    else:
        form = EnvironmentForm()
    return render(request, 'environments/form.html', {'form': form, 'title': 'New Environment'})


@login_required
def environment_detail(request, pk):
    env = get_object_or_404(Environment, pk=pk, owner=request.user)
    services = env.services.order_by('sort_order', 'service_type', 'name')
    memberships = env.memberships.select_related('user').order_by('role', 'user__first_name')

    # Users that can be added: all users visible to this owner that aren't already members
    existing_user_ids = memberships.values_list('user_id', flat=True)
    addable_users = User.objects.exclude(pk__in=existing_user_ids).exclude(pk=request.user.pk).order_by('first_name', 'last_name', 'email')

    return render(request, 'environments/detail.html', {
        'environment': env,
        'services': services,
        'memberships': memberships,
        'addable_users': addable_users,
    })


@login_required
def environment_edit(request, pk):
    env = get_object_or_404(Environment, pk=pk, owner=request.user)
    if request.method == 'POST':
        form = EnvironmentForm(request.POST, instance=env)
        if form.is_valid():
            form.save()
            messages.success(request, 'Environment updated.')
            return redirect('environments:detail', pk=env.pk)
    else:
        form = EnvironmentForm(instance=env)
    return render(request, 'environments/form.html', {'form': form, 'title': 'Edit Environment', 'environment': env})


@login_required
def environment_delete(request, pk):
    env = get_object_or_404(Environment, pk=pk, owner=request.user)
    if request.method == 'POST':
        env.delete()
        messages.success(request, 'Environment deleted.')
        return redirect('environments:list')
    return render(request, 'environments/confirm_delete.html', {'environment': env})


# ──────────────────────────────────────────────
# Member management
# ──────────────────────────────────────────────

@login_required
@require_POST
def environment_member_add(request, pk):
    env = get_object_or_404(Environment, pk=pk, owner=request.user)
    user_id = request.POST.get('user_id')
    role = request.POST.get('role', 'env_member')
    if role not in ('env_admin', 'env_member'):
        role = 'env_member'

    user = get_object_or_404(User, pk=user_id)
    membership, created = EnvironmentMembership.objects.get_or_create(
        environment=env, user=user,
        defaults={'role': role},
    )
    if not created:
        membership.role = role
        membership.save()
        messages.success(request, f'{user.display_name} role updated to {membership.get_role_display()}.')
    else:
        messages.success(request, f'{user.display_name} added as {membership.get_role_display()}.')

    return redirect('environments:detail', pk=pk)


@login_required
@require_POST
def environment_member_remove(request, pk, user_pk):
    env = get_object_or_404(Environment, pk=pk, owner=request.user)
    membership = get_object_or_404(EnvironmentMembership, environment=env, user_id=user_pk)
    name = membership.user.display_name
    membership.delete()
    messages.success(request, f'{name} removed from environment.')
    return redirect('environments:detail', pk=pk)


@login_required
@require_POST
def environment_member_role(request, pk, user_pk):
    env = get_object_or_404(Environment, pk=pk, owner=request.user)
    membership = get_object_or_404(EnvironmentMembership, environment=env, user_id=user_pk)
    role = request.POST.get('role', 'env_member')
    if role not in ('env_admin', 'env_member'):
        role = 'env_member'
    membership.role = role
    membership.save()
    messages.success(request, f'{membership.user.display_name} is now {membership.get_role_display()}.')
    return redirect('environments:detail', pk=pk)
