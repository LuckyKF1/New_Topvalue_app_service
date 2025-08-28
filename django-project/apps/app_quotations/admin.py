from django.contrib import admin
from apps.app_employee.models import EmployeesModel
from .models import (
    GenerateQuotationID,
    QuotationInformationModel,
    QuotationItemsModel,
    AdditionalExpensesModel
)

# Inline for Quotation Items Model
class QuotationItemsInline(admin.TabularInline):
    model = QuotationItemsModel
    extra = 1
    fields = ['product_name', 'price', 'qty', 'period']
    readonly_fields = ['total_one_product']

# Inline for Additional Expenses Model
class AdditionalExpensesInline(admin.TabularInline):
    model = AdditionalExpensesModel
    extra = 1
    max_num = 1
    # readonly_fields = [
    #     'total_all_product_ref',  
    #     'it_service_output',     
    #     'vat_output',             
    #     'exchange_rate_output',   
    #     'grand_total',            
    # ]
    fields = [
        'it_service_percent',
        'vat_percent',
        'exchange_rate',
        # 'total_all_product_ref',
        # 'it_service_output',
        # 'vat_output',
        # 'exchange_rate_output',
        # 'grand_total',
    ]

# QuotationInformationModel for Admin
@admin.register(QuotationInformationModel)
class QuotationInformationModelAdmin(admin.ModelAdmin):
    list_display = [
        'quotation_id',
        'customer',
        'start_date',
        'end_date',
        'status',
    ]
    list_filter = [
        'status',
        'start_date',
        'end_date'
    ]
    search_fields = [
        'quotation_id', 
        'customer__company_name',
        'customer__contact_person_name',
        'status'
    ]
    autocomplete_fields = ["customer", "created_by"]
    inlines = [QuotationItemsInline, AdditionalExpensesInline]
    readonly_fields = ['quotation_id']
    
    # Hide these fields on add/edit form
    exclude = [
        'created_at_log',
        'updated_at_log',
    ]

    def save_model(self, request, obj, form, change):
        try:
            employee = EmployeesModel.objects.get(user=request.user)
        except EmployeesModel.DoesNotExist:
            employee = None 

        super().save_model(request, obj, form, change)
