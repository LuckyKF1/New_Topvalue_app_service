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
    path('create/<uuid:po_id>/', views.ContractsCreateView.as_view(), name='create_contract'),
    path('', views.ContractsListView.as_view(), name='home'),
]

# when user go to path /app_name/ it will show api root page (endpoints list)
urlpatterns += router.urls
