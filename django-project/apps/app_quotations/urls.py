# coding=utf-8
# django libs
from django.urls import path, include

# 3rd party libs
from rest_framework.routers import DefaultRouter

# custom import
from . import views

# Namespace for URLs in this users app
app_name = 'app_quotations'
router = DefaultRouter()
# router.register('', views.ViewSet)

urlpatterns = [
    path('api/', include(router.urls)),
    path('', views.HomeView.as_view(), name='home'),
    path('CreateQuotationView/', views.CreateQuotationView.as_view(), name='create_quotation'),
    path('UpdateView/<str:quotation_id>/', views.UpdateView.as_view(), name='update_quotation'),
    path('Delete/<str:quotation_id>', views.DeleteView.as_view(), name='delete_quotation'),
    path('quotation_details/<str:quotation_id>/', views.QuotationDetailView.as_view(), name='quotation_details'),
    path('quotation_details/quotation_form/<str:quotation_id>/', views.OneQuotationDetailsView.as_view(), name='generate_quotation_form'),
    path('quotation_details/quotation_form/generate_pdf/<str:quotation_id>/', views.GenerateQuotationPDF.as_view(), name='quotation_generator_pdf'),
    path('quotation_details/quotation_form/generate_pdf_no_sig/<str:quotation_id>/', views.GenerateQuotationPDFNoSig.as_view(), name='quotation_generator_pdf_no_sig'),
    # path('quotation_details/quotation_form/quotation_pdf_generator/<str:quotation_id>/', views.quotation_generator_pdf, name='quotation_generator_pdf'),
    # path('quotation_details/quotation_form/quotation_generator_pdf_no_sig/<str:quotation_id>/', views.quotation_generator_pdf_no_sig, name='quotation_generator_pdf_no_sig'),
]

# when user go to path /app_name/ it will show api root page (endpoints list)
urlpatterns += router.urls
