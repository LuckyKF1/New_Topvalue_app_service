# coding=utf-8
from django.contrib import admin
from apps.app_employee.models import EmployeesModel
from .models import PoIdGeneratorModel, PurchaseOrderModel, PurchaseOrderItemsModel, ApprovedPOModel

@admin.register(ApprovedPOModel)
class ApprovedPOModelAdmin(admin.ModelAdmin):
    list_display = ['name', 'last_name', 'position']
    

# inline for PO items model
class PurchaseOrderItemsInline(admin.TabularInline):
    model = PurchaseOrderItemsModel
    extra = 1
    fields = ['product_name', 'price', 'qty', 'period', 'total_one_product']
    readonly_fields = ['total_one_product']


@admin.register(PurchaseOrderModel)
class PurchaseOrderModelAdmin(admin.ModelAdmin):
    list_display = [
        'po_id',
        'customer',
        'start_date',
        'end_date',
        'status',
    ]
    list_filter = [
        'status',
        'start_date',
        'end_date',
    ]
    search_fields = [
        'po_id',
        'quotation__customer__company_name',
        'quotation__customer__contact_person_name',
        'status'
    ]
    autocomplete_fields = ["quotation", "created_by"]
    inlines = [PurchaseOrderItemsInline]
    readonly_fields = ['po_id']
    exclude = [
        'created_at_log',
        'updated_at_log',
    ]

    def customer(self, obj):
        return obj.quotation.customer.company_name if obj.quotation and obj.quotation.customer else "-"
    customer.admin_order_field = 'quotation__customer__company_name'
    customer.short_description = 'ລູກຄ້າ'

    def save_model(self, request, obj, form, change):
        if not obj.created_by_id:
            try:
                employee = EmployeesModel.objects.get(user=request.user)
                obj.created_by = employee
            except EmployeesModel.DoesNotExist:
                pass
        super().save_model(request, obj, form, change)
