# coding=utf-8
# django libs
from django.urls import path, include

# 3rd party libs
from rest_framework.routers import DefaultRouter

# custom import
from . import views

# Namespace for URLs in this users app
app_name = 'app_contracts'
router = DefaultRouter()
# router.register('', views.ViewSet)

urlpatterns = [
    path('api/', include(router.urls)),
    path('create_from_po/<str:po_id>/', views.ContractsCreateView.as_view(), name='create_contract_from_po'),
    path('', views.ContractsListView.as_view(), name='home'),
    path('delete_contract/<str:contract_id>/', views.ContractDeleteView.as_view(), name='delete'),
    path('contract_details/<str:contract_id>/', views.ContractDetailsView.as_view(), name='contract_details'),
    path('contract_details/update_contract/<str:contract_id>/', views.UpdateContractView.as_view(), name='update_contract')
]

# when user go to path /app_name/ it will show api root page (endpoints list)
urlpatterns += router.urls
