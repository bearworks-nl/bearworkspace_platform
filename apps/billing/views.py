from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from .models import Plan, Subscription, Invoice


@login_required
def billing_overview(request):
    subscriptions = Subscription.objects.filter(user=request.user).select_related('plan', 'service')
    invoices = Invoice.objects.filter(user=request.user)[:10]
    plans = Plan.objects.filter(is_active=True)
    return render(request, 'billing/overview.html', {
        'subscriptions': subscriptions,
        'invoices': invoices,
        'plans': plans,
    })


@login_required
def invoice_list(request):
    invoices = Invoice.objects.filter(user=request.user)
    return render(request, 'billing/invoice_list.html', {'invoices': invoices})


@login_required
def invoice_detail(request, pk):
    invoice = get_object_or_404(Invoice, pk=pk, user=request.user)
    return render(request, 'billing/invoice_detail.html', {'invoice': invoice})


@login_required
def subscription_cancel(request, pk):
    sub = get_object_or_404(Subscription, pk=pk, user=request.user)
    if request.method == 'POST':
        sub.status = 'canceled'
        sub.save()
        messages.success(request, 'Subscription canceled.')
        return redirect('billing:overview')
    return render(request, 'billing/subscription_cancel.html', {'subscription': sub})


@login_required
def plan_list(request):
    plans = Plan.objects.filter(is_active=True)
    return render(request, 'billing/plan_list.html', {'plans': plans})


def mollie_webhook(request):
    # Handle Mollie webhook
    from django.http import HttpResponse
    return HttpResponse('ok')
