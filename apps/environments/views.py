import json
from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.http import JsonResponse
from django.utils.text import slugify
from django.views.decorators.http import require_POST
from django import forms
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
    """
    Accepts a JSON body: {"order": [3, 1, 5, 2, ...]}
    (a list of environment PKs in the new desired order).
    Updates sort_order for each environment owned by this user.
    """
    try:
        data = json.loads(request.body)
        order = data.get('order', [])
    except (json.JSONDecodeError, AttributeError):
        return JsonResponse({'error': 'Invalid JSON'}, status=400)

    # Only allow updating environments this user owns
    owned_ids = set(
        Environment.objects.filter(owner=request.user).values_list('pk', flat=True)
    )

    updates = []
    for position, pk in enumerate(order):
        pk = int(pk)
        if pk in owned_ids:
            updates.append((pk, position))

    for pk, position in updates:
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
            # Place new environments at the end
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
    services = env.services.all()
    return render(request, 'environments/detail.html', {'environment': env, 'services': services})


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
