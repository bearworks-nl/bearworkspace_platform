from django.shortcuts import render, redirect
from django.contrib.auth.decorators import login_required
from apps.environments.models import Environment
from apps.services.models import Service
from apps.billing.models import Subscription, Invoice


def landing(request):
    if request.user.is_authenticated:
        return redirect('core:dashboard')
    return render(request, 'core/landing.html')


@login_required
def dashboard(request):
    environments = Environment.objects.filter(owner=request.user).order_by('sort_order', 'name')
    services = Service.objects.filter(environment__owner=request.user, enabled=True)
    recent_invoices = Invoice.objects.filter(user=request.user)[:5]
    active_subscriptions = Subscription.objects.filter(user=request.user, status__in=['active', 'trialing'])

    stats = {
        'environments': environments.count(),
        'services': services.count(),
        'subscriptions': active_subscriptions.count(),
        'invoices_unpaid': Invoice.objects.filter(user=request.user, status='open').count(),
    }

    return render(request, 'core/dashboard.html', {
        'environments': environments[:5],
        'services': services[:6],
        'recent_invoices': recent_invoices,
        'stats': stats,
    })
