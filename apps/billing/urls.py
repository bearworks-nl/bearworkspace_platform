from django.urls import path
from . import views

app_name = 'billing'

urlpatterns = [
    path('', views.billing_overview, name='overview'),
    path('invoices/', views.invoice_list, name='invoice_list'),
    path('invoices/<uuid:pk>/', views.invoice_detail, name='invoice_detail'),
    path('subscriptions/<int:pk>/cancel/', views.subscription_cancel, name='subscription_cancel'),
    path('plans/', views.plan_list, name='plan_list'),
    path('webhook/', views.mollie_webhook, name='mollie_webhook'),
]
