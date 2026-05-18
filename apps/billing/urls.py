from django.urls import path
from . import views

app_name = "billing"

urlpatterns = [
    # Plans
    path("plans/", views.PlanListView.as_view(), name="plan_list"),
    path("plans/create/", views.PlanCreateView.as_view(), name="plan_create"),
    path("plans/<uuid:pk>/edit/", views.PlanUpdateView.as_view(), name="plan_edit"),
    path("plans/<uuid:pk>/toggle/", views.PlanToggleView.as_view(), name="plan_toggle"),
    # Subscriptions
    path("subscriptions/", views.SubscriptionListView.as_view(), name="subscription_list"),
    path("subscriptions/<uuid:pk>/", views.SubscriptionDetailView.as_view(), name="subscription_detail"),
    path("subscriptions/<uuid:pk>/edit/", views.SubscriptionEditView.as_view(), name="subscription_edit"),
    path("subscriptions/<uuid:subscription_pk>/setup-mandate/", views.SetupMandateView.as_view(), name="setup_mandate"),
    # Invoices
    path("invoices/", views.InvoiceListView.as_view(), name="invoice_list"),
    path("invoices/<uuid:pk>/", views.InvoiceDetailView.as_view(), name="invoice_detail"),
    path("invoices/<uuid:pk>/download/", views.InvoiceDownloadView.as_view(), name="invoice_download"),
    # Mollie webhook
    path("webhook/mollie/", views.MollieWebhookView.as_view(), name="mollie_webhook"),
]
