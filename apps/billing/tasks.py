from celery import shared_task
from django.utils import timezone
from datetime import date, timedelta
from decimal import Decimal
import logging

logger = logging.getLogger(__name__)


def _get_unit_count(subscription):
    """Count billable units for a subscription based on its product type."""
    from apps.products.models import ProductType, CloudPC
    product = subscription.product
    pt = product.product_type

    if pt == ProductType.RECAST_WORKSPACE:
        # Count users with access to this organisation
        from apps.organisations.models import OrganisationMembership
        return OrganisationMembership.objects.filter(
            organisation=product.organisation
        ).count()

    elif pt == ProductType.WINDOWS_365:
        # Count provisioned Cloud PCs
        try:
            return CloudPC.objects.filter(
                config__product=product,
                status=CloudPC.Status.PROVISIONED,
            ).count()
        except Exception:
            return 0

    elif pt == ProductType.INTUNE:
        # Billed per organisation (flat = 1 unit)
        return 1

    return 0


@shared_task(name="billing.snapshot_usage")
def snapshot_usage():
    """
    Run monthly (via Celery beat) to capture usage for all active subscriptions
    and generate invoices.
    """
    from apps.billing.models import Subscription, UsageSnapshot, Invoice

    today = date.today()
    # Snapshot covers previous month
    period_end = today.replace(day=1) - timedelta(days=1)
    period_start = period_end.replace(day=1)

    active_subs = Subscription.objects.filter(
        status__in=[Subscription.Status.ACTIVE]
    ).select_related("plan", "product__organisation__customer")

    for sub in active_subs:
        # Skip if snapshot already exists
        if UsageSnapshot.objects.filter(subscription=sub, period_start=period_start).exists():
            logger.info("Snapshot already exists for %s %s", sub, period_start)
            continue

        unit_count = _get_unit_count(sub)
        snapshot = UsageSnapshot.objects.create(
            subscription=sub,
            period_start=period_start,
            period_end=period_end,
            unit_count=unit_count,
            unit_type=sub.plan.unit_type,
        )
        logger.info("Snapshot created: %s — %d units", sub, unit_count)

        # Generate invoice
        amount = sub.calculate_amount(unit_count)
        if amount > Decimal("0.00"):
            invoice = Invoice.objects.create(
                subscription=sub,
                usage_snapshot=snapshot,
                amount=amount,
                currency=sub.plan.currency,
                period_start=period_start,
                period_end=period_end,
                issued_at=timezone.now(),
                due_at=timezone.now() + timedelta(days=14),
            )
            logger.info("Invoice created: %s for %s", invoice.invoice_number, amount)
            # Trigger payment async
            charge_invoice_task.delay(str(invoice.id))


@shared_task(name="billing.charge_invoice")
def charge_invoice_task(invoice_id):
    """Charge a single invoice via Mollie."""
    from apps.billing.models import Invoice
    from apps.billing.mollie_service import charge_invoice

    try:
        invoice = Invoice.objects.select_related(
            "subscription__product__organisation__customer"
        ).get(id=invoice_id)
        customer = invoice.subscription.product.organisation.customer
        charge_invoice(customer, invoice)
        logger.info("Mollie payment triggered for invoice %s", invoice.invoice_number)
    except Invoice.DoesNotExist:
        logger.error("Invoice %s not found", invoice_id)
    except Exception as e:
        logger.error("Charge failed for invoice %s: %s", invoice_id, e)
        raise


@shared_task(name="billing.generate_pdf")
def generate_invoice_pdf(invoice_id):
    """Generate a PDF for an invoice using ReportLab."""
    from apps.billing.models import Invoice
    from reportlab.lib.pagesizes import A4
    from reportlab.pdfgen import canvas
    from django.core.files.base import ContentFile
    import io

    try:
        invoice = Invoice.objects.select_related(
            "subscription__product__organisation__customer"
        ).get(id=invoice_id)

        buffer = io.BytesIO()
        c = canvas.Canvas(buffer, pagesize=A4)
        width, height = A4

        c.setFont("Helvetica-Bold", 18)
        c.drawString(50, height - 60, "Invoice")

        c.setFont("Helvetica", 11)
        c.drawString(50, height - 90, f"Invoice number: {invoice.invoice_number}")
        c.drawString(50, height - 108, f"Date: {invoice.issued_at.strftime('%d %B %Y') if invoice.issued_at else '—'}")
        c.drawString(50, height - 126, f"Period: {invoice.period_start} – {invoice.period_end}")

        customer = invoice.subscription.product.organisation.customer
        c.drawString(50, height - 160, f"Customer: {customer.name}")
        c.drawString(50, height - 178, f"Organisation: {invoice.subscription.product.organisation.name}")
        c.drawString(50, height - 196, f"Product: {invoice.subscription.product.get_product_type_display()}")

        c.line(50, height - 220, width - 50, height - 220)

        c.drawString(50, height - 245, f"Units: {invoice.usage_snapshot.unit_count if invoice.usage_snapshot else '—'}")
        c.drawString(50, height - 263, f"Amount excl. VAT: {invoice.currency} {invoice.amount:.2f}")
        c.drawString(50, height - 281, f"VAT ({invoice.tax_rate}%): {invoice.currency} {invoice.tax_amount:.2f}")
        c.setFont("Helvetica-Bold", 11)
        c.drawString(50, height - 305, f"Total: {invoice.currency} {invoice.total_amount:.2f}")

        c.save()
        buffer.seek(0)
        invoice.pdf.save(
            f"{invoice.invoice_number}.pdf",
            ContentFile(buffer.read()),
            save=True,
        )
        logger.info("PDF generated for invoice %s", invoice.invoice_number)
    except Exception as e:
        logger.error("PDF generation failed for invoice %s: %s", invoice_id, e)
        raise
