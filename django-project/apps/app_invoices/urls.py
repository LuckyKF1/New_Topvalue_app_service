# coding=utf-8
# django libs
from django.urls import path, include

# 3rd party libs
from rest_framework.routers import DefaultRouter

# custom import
from . import views

# Namespace for URLs in this users app
app_name = 'app_invoices'
router = DefaultRouter()
# router.register('', views.ViewSet)

urlpatterns = [
    path('api/', include(router.urls)),
    path('<str:invoice_id>/', views.CreateInvoice.as_view(), name='create_invoice'),
    path('', views.InvoiceListView.as_view(), name='home'),
    path('delete_invoice/<str:invoice_id>/', views.DeleteInvoiceView.as_view(), name='delete_invoice'),
    path('invoice_details/<str:invoice_id>/', views.InvoiceDetailsView.as_view(), name='invoice_details'),
    path('invoice_details/update/<str:invoice_id>/', views.UpdateInvoiceView.as_view(), name='update_invoice'),
    path('invoice_details/view_invoice_form/<str:invoice_id>/', views.OneInvoiceDetailsView.as_view(), name='invoice_view_form'),
    path('invoice_details/view_invoice_form/download_pdf/<str:invoice_id>/', views.GenerateInvoicePDF.as_view(), name='generate_invoice_pdf'),
    path('invoice_details/view_invoice_form/download_pdf_no_sig/<str:invoice_id>/', views.GenerateInvoicePDFNoSig.as_view(), name='generate_invoice_pdf_no_sig'),
]

# when user go to path /app_name/ it will show api root page (endpoints list)
urlpatterns += router.urls
