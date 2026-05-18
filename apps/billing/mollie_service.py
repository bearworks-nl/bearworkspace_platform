"""
Mollie integration service.
Wraps the mollie-api-python client for subscriptions, mandates, and payments.
"""
from django.conf import settings
from mollie.api.client import Client
from mollie.api.error import Error as MollieError
import logging

logger = logging.getLogger(__name__)


def get_client():
    client = Client()
    client.set_api_key(settings.MOLLIE_API_KEY)
    return client


def create_mollie_customer(customer):
    """Create a Mollie customer record and store the ID."""
    client = get_client()
    try:
        mollie_customer = client.customers.create({
            "name": customer.name,
            "email": customer.email,
            "metadata": {"customer_id": str(customer.id)},
        })
        customer.mollie_customer_id = mollie_customer["id"]
        customer.save(update_fields=["mollie_customer_id"])
        return mollie_customer
    except MollieError as e:
        logger.error("Mollie create customer failed: %s", e)
        raise


def create_first_payment(customer, subscription, redirect_url):
    """
    Create a first payment to establish a mandate for recurring billing.
    Returns the Mollie payment checkout URL.
    """
    client = get_client()
    if not customer.mollie_customer_id:
        create_mollie_customer(customer)
    try:
        payment = client.customer_payments.with_parent_id(
            customer.mollie_customer_id
        ).create({
            "amount": {"currency": subscription.plan.currency, "value": "0.01"},
            "description": f"Mandate for {subscription.plan.name}",
            "redirectUrl": redirect_url,
            "webhookUrl": settings.MOLLIE_WEBHOOK_URL,
            "sequenceType": "first",
            "metadata": {"subscription_id": str(subscription.id)},
        })
        return payment["_links"]["checkout"]["href"]
    except MollieError as e:
        logger.error("Mollie first payment failed: %s", e)
        raise


def create_mollie_subscription(customer, subscription):
    """Create a Mollie subscription after mandate is established."""
    client = get_client()
    plan = subscription.plan
    interval = "1 month" if plan.interval == "monthly" else "12 months"
    try:
        mollie_sub = client.customer_subscriptions.with_parent_id(
            customer.mollie_customer_id
        ).create({
            "amount": {
                "currency": plan.currency,
                "value": f"{subscription.calculate_amount(1):.2f}",
            },
            "interval": interval,
            "description": f"{plan.name} — {subscription.product.organisation.name}",
            "webhookUrl": settings.MOLLIE_WEBHOOK_URL,
            "metadata": {"subscription_id": str(subscription.id)},
        })
        subscription.mollie_subscription_id = mollie_sub["id"]
        subscription.status = "active"
        subscription.save(update_fields=["mollie_subscription_id", "status"])
        return mollie_sub
    except MollieError as e:
        logger.error("Mollie create subscription failed: %s", e)
        raise


def cancel_mollie_subscription(customer, subscription):
    """Cancel a Mollie subscription."""
    client = get_client()
    if not subscription.mollie_subscription_id:
        return
    try:
        client.customer_subscriptions.with_parent_id(
            customer.mollie_customer_id
        ).delete(subscription.mollie_subscription_id)
    except MollieError as e:
        logger.error("Mollie cancel subscription failed: %s", e)
        raise


def charge_invoice(customer, invoice):
    """
    Trigger a one-off Mollie payment for a usage-based invoice
    against the customer's existing mandate.
    """
    client = get_client()
    try:
        payment = client.customer_payments.with_parent_id(
            customer.mollie_customer_id
        ).create({
            "amount": {
                "currency": invoice.currency,
                "value": f"{invoice.total_amount:.2f}",
            },
            "description": f"Invoice {invoice.invoice_number}",
            "webhookUrl": settings.MOLLIE_WEBHOOK_URL,
            "sequenceType": "recurring",
            "metadata": {"invoice_id": str(invoice.id)},
        })
        invoice.mollie_payment_id = payment["id"]
        invoice.status = "open"
        invoice.save(update_fields=["mollie_payment_id", "status"])
        return payment
    except MollieError as e:
        logger.error("Mollie charge invoice failed: %s", e)
        raise


def handle_webhook(payment_id):
    """
    Process a Mollie webhook notification.
    Called by the webhook view after verifying the request.
    """
    from apps.billing.models import Invoice
    from django.utils import timezone

    client = get_client()
    payment = client.payments.get(payment_id)
    metadata = payment.get("metadata", {})

    # Handle invoice payment
    if "invoice_id" in metadata:
        try:
            invoice = Invoice.objects.get(id=metadata["invoice_id"])
            mollie_status = payment["status"]
            if mollie_status == "paid":
                invoice.status = Invoice.Status.PAID
                invoice.paid_at = timezone.now()
            elif mollie_status in ("failed", "expired", "canceled"):
                invoice.status = Invoice.Status.FAILED
                invoice.subscription.status = "past_due"
                invoice.subscription.save(update_fields=["status"])
            invoice.save(update_fields=["status", "paid_at"])
        except Invoice.DoesNotExist:
            logger.warning("Webhook for unknown invoice %s", metadata["invoice_id"])
