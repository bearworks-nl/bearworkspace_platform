from django.shortcuts import render, redirect
from django.contrib.auth.decorators import login_required
from apps.environments.models import Environment
from apps.services.models import Service
from apps.billing.models import Subscription, Invoice
from django.utils import timezone

def landing(request):
    return render(request, 'core/landing.html')


@login_required
def dashboard(request):
    environments = Environment.objects.filter(owner=request.user).order_by('sort_order', 'name')
    services = Service.objects.filter(environment__owner=request.user, enabled=True)
    recent_invoices = Invoice.objects.filter(user=request.user)[:5]
    active_subscriptions = Subscription.objects.filter(user=request.user, status__in=['active', 'trialing'])

    hour = timezone.localtime(timezone.now()).hour
    if hour < 6:
        greeting = "Up late"
    elif hour < 12:
        greeting = "Good morning"
    elif hour < 18:
        greeting = "Good afternoon"
    elif hour < 00:
        greeting = "Good evening"
    else:
        greeting = "Up late"

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
        'greeting': greeting,
    })
