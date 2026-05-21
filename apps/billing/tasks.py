from celery import shared_task
from django.utils import timezone
from django.conf import settings
import logging

logger = logging.getLogger(__name__)


@shared_task
def generate_monthly_invoices():
    """
    Run on the 1st of each month via Celery Beat.
    Snapshots usage for each active subscription and creates invoices.
    """
    from apps.billing.models import Subscription, UsageSnapshot, Invoice
    from apps.accounts.models import User
    import uuid
    from datetime import date
    from calendar import monthrange

    today = date.today()
    first_of_month = today.replace(day=1)

    if today.month == 1:
        prev_month = today.replace(year=today.year - 1, month=12, day=1)
    else:
        prev_month = today.replace(month=today.month - 1, day=1)

    _, last_day = monthrange(prev_month.year, prev_month.month)
    period_end = prev_month.replace(day=last_day)

    active_subs = Subscription.objects.filter(
        status__in=['active', 'trialing']
    ).select_related('user', 'plan', 'service')

    created_count = 0
    for sub in active_subs:
        # Check if invoice already exists for this period
        existing = Invoice.objects.filter(
            subscription=sub,
            period_start=prev_month,
            period_end=period_end,
        ).exists()

        if existing:
            continue

        # Snapshot usage
        quantity = 1
        if sub.service:
            if hasattr(sub.service, 'recast_config'):
                quantity = sub.service.recast_config.workspace_count or 1
            elif hasattr(sub.service, 'w365_config'):
                quantity = sub.service.w365_config.device_count or 1

        UsageSnapshot.objects.create(
            subscription=sub,
            quantity=quantity,
            period_start=prev_month,
            period_end=period_end,
        )

        amount = sub.plan.price_per_unit * quantity
        tax_amount = amount * 21 / 100  # 21% VAT NL

        invoice_number = f"INV-{prev_month.strftime('%Y%m')}-{str(sub.pk).zfill(4)}"

        Invoice.objects.create(
            user=sub.user,
            subscription=sub,
            invoice_number=invoice_number,
            amount=amount,
            tax_amount=tax_amount,
            status='open',
            period_start=prev_month,
            period_end=period_end,
            due_date=today.replace(day=14),
        )
        created_count += 1

    logger.info(f'Generated {created_count} invoices for {prev_month.strftime("%B %Y")}')
    return f'Created {created_count} invoices'


@shared_task
def charge_open_invoices():
    """Trigger Mollie recurring charge for open invoices."""
    from apps.billing.models import Invoice

    open_invoices = Invoice.objects.filter(status='open').select_related('user')
    charged = 0

    for invoice in open_invoices:
        try:
            # TODO: integrate Mollie API here
            # mollie_service.charge_recurring(invoice)
            logger.info(f'Would charge invoice {invoice.invoice_number} via Mollie')
            charged += 1
        except Exception as e:
            logger.error(f'Failed to charge invoice {invoice.invoice_number}: {e}')

    return f'Processed {charged} invoices'
