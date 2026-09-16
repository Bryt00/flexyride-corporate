from django.urls import path
from . import views

app_name = 'payments'

urlpatterns = [
    path('requests/<str:request_id>/pay/', views.payment_view, name='payment'),
    path('requests/<str:request_id>/payment-success/', views.payment_success_view, name='payment_success'),
    path('invoices/', views.customer_invoices_view, name='customer_invoices'),
    path('receipts/<str:receipt_ref>/print/', views.receipt_printable_view, name='receipt_printable'),
    path('invoices/<str:invoice_num>/print/', views.invoice_printable_view, name='invoice_printable'),
    path('paystack/webhook/', views.paystack_webhook_view, name='paystack_webhook'),
    path('broker/financials/', views.broker_financials_view, name='broker_financials'),
    path('provider/payouts/', views.provider_payouts_view, name='provider_payouts'),
]
