# coding=utf-8
# django libs
from django.urls import path, include

# 3rd party libs
from rest_framework.routers import DefaultRouter

# custom import
from . import views

# Namespace for URLs in this users app
app_name = 'app_po'
router = DefaultRouter()
# router.register('', views.ViewSet)

urlpatterns = [
    path('api/', include(router.urls)),
    path('create_po/from-invoice/<str:invoice_id>/', views.PurchaseOrderCreateView.as_view(), name='create_po_from_invoice'),
    path('', views.HomeView.as_view(), name='home'),
    path('delete_po/<str:po_id>/', views.DeleteView.as_view(), name='delete_po'),
    path('po_details/<str:po_id>/', views.InvoiceDetailsView.as_view(), name='po_details'),
    path('po_details/update/<str:po_id>/', views.PurchaseOrderUpdateView.as_view(), name='update_po'),
    path('po_details/view_po_form/<str:po_id>/', views.OnePoDetailsView.as_view(), name='po_view_form'),
    path('po_details/view_po_form/download_pdf/<str:po_id>/', views.GeneratePoPdfView.as_view(), name='generate_po_pdf'),
]

# when user go to path /app_name/ it will show api root page (endpoints list)
urlpatterns += router.urls
