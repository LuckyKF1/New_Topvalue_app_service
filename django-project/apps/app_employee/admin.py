# coding=utf-8
from django.contrib import admin
from apps.app_employee.models import EmployeesModel


@admin.register(EmployeesModel)
class EmployeesModelAdmin(admin.ModelAdmin):
    list_display = ['employee_name', 'employee_lastname', 'department', 'create_date']
    search_fields = ['employee_name', 'employee_lastname', 'department']
    ordering = ('employee_id',)
    readonly_fields =('employee_id',)