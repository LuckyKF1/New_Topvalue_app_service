# coding=utf-8
from django.contrib import admin

# Import Models
from .models import ContractsModel

# Register ModelAdmin Here
@admin.register(ContractsModel)
class ContractsModelAdmin(admin.ModelAdmin):
    list_display = ['customer__company_name', 'status', 'start_contract', 'end_contract']
    list_filter = ['status', 'start_contract', 'end_contract']
    search_fields = ['customer__company_name', 'status']