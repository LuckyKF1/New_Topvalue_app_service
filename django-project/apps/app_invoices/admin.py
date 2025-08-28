# coding=utf-8
from django.contrib import admin
from apps.app_employee.models import EmployeesModel
from .models import InvoiceModel

@admin.register(InvoiceModel)
class InvoiceModelAdmin(admin.ModelAdmin):
    list_display = ['invoice_id', 'quotation__customer__company_name', 'issue_date', 'due_date', 'status', 'created_by']
    list_filter = ['issue_date', 'due_date', 'status']
    readonly_fields = ['invoice_id',]

    def save_model(self, request, obj, form, change):
        try:
            employee = EmployeesModel.objects.get(user=request.user)
        except EmployeesModel.DoesNotExist:
            employee = None
        super().save_model(request, obj, form, change)


'''
# snipet

@admin.register(ModelName)
class ModelNameAdmin(admin.ModelAdmin):
    list_display = ['field1', 'field2',]

@admin.register(ModelName)
class ModelNameAdmin(admin.ModelAdmin):
    pass
'''
