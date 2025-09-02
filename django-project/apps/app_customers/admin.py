# coding=utf-8
from django.contrib import admin


#Model
from .models import CustomersModel, CustomerTenantModel


#Register ModelAdmin Here
@admin.register(CustomerTenantModel)
class CustomerTenantModelAdmin(admin.ModelAdmin):
    list_display = ['tenant_name', 'tenant_domain']


@admin.register(CustomersModel)
class CustomersModelAdmin(admin.ModelAdmin):
    list_display = ['customer_id', 'company_name', 'contact_person_name', 'phone_number', 'email', 'create_at']
    search_fields = ['customer_id', 'company_name', 'contact_person_name', 'phone_number', 'email']
    ordering = ['-create_at',]
    readonly_fields = ['customer_id', 'create_at']