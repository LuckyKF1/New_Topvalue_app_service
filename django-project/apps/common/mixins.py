# coding=utf-8
from django.db import models
from decimal import Decimal
from django.db.models import Sum
from django.utils import timezone as tz
from apps.app_customers.models import CustomersModel
from apps.app_employee.models import EmployeesModel

# Common models and utilities for the Django project
# This file can contain shared models, utilities, or constants that are used across multiple apps.

class CommonInformationModelMixins(models.Model):
    class Status(models.TextChoices):
        PENDING = 'pending', 'ລໍຖ້າອະນຸມັດ'
        COMPLETED = 'completed', 'ສຳເລັດ'
        REJECTED = 'rejected', 'ປະຕິເສດ'
        CANCELLED = 'cancelled', 'ຍົກເລີກ'
        BANNED = 'banned', 'ຖືກລະງັບ'
        
    class Meta:
        abstract = True
        # This model is abstract, meaning it won't create a table in the database
        # but can be inherited by other models to share common fields or methods.
    customer = models.ForeignKey(CustomersModel, on_delete=models.CASCADE, related_name='customers', verbose_name='ລູກຄ້າ')
    created_by = models.ForeignKey(EmployeesModel, on_delete=models.CASCADE, related_name='created_by', verbose_name='ສ້າງໂດຍ')
    created_at_log = models.DateTimeField(verbose_name='ວັນເວລາສ້າງ', default=tz.now)
    updated_at_log = models.DateTimeField(verbose_name="ວັນທີອັບເດດຂໍ້ມູນ", auto_now=True)
    status = models.CharField(max_length=20, choices=Status.choices, default=Status.PENDING, verbose_name='ສະຖານະ')
    total_all_products = models.DecimalField(max_digits=10, decimal_places=2, default=Decimal('0.00'), editable=False, blank=True, null=True, verbose_name='ລາຄາລວມທັງໝົດ')

    # Calculate total_all_products based on related items
    def calculate_total_all_products(self):
        total_sum = self.items.aggregate(total=Sum('total_one_product'))['total']
        # If no items are found, total_sum will be None
        # We set it to 0.00 if it's None to avoid errors in calculations
        if total_sum is None:
            total_sum = Decimal('0.00')
        
        if self.total_all_products != total_sum:
            self.total_all_products = total_sum
            super(CommonInformationModelMixins, self).save(update_fields=['total_all_products'])

    
# Common ItemsModel for shared fields
class CommonItemsModelMixins(models.Model):
    class Meta:
        abstract = True
        # This model is abstract, meaning it won't create a table in the database
        # but can be inherited by other models to share common fields or methods.
    common_information = models.ForeignKey(CommonInformationModelMixins, on_delete=models.CASCADE, related_name='items', verbose_name='ຂໍ້ມູນທົ່ວໄປ')
    product_name = models.CharField(max_length=255, verbose_name='ຊື່ສິນຄ້າ')
    price = models.DecimalField(max_digits=10, decimal_places=2, default=Decimal('0.00'), verbose_name='ລາຄາ')
    qty = models.PositiveIntegerField(default=1, verbose_name='ຈຳນວນ')
    period = models.PositiveIntegerField(default=12, verbose_name='ລະດັບເວລາ (ເດືອນ)')
    total_one_product = models.DecimalField(max_digits=10, decimal_places=2, default=Decimal('1'), editable=False, blank=True, null=True, verbose_name='ລາຄາລວມ')

    # Calculate total_one_product based on price and qty
    def save(self, *args, **kwargs):
        if self.price is not None and self.qty is not None and self.period is not None:
            self.total_one_product = self.price * self.qty * self.period
        else:
            self.total_one_product = Decimal('0.00')
        super().save(*args, **kwargs)

        # After save the item, trigger the update of total_all_products in CommonInformationModel
        self.common_information.calculate_total_all_products()
    # Delete
    def delete(self, *args, **kwargs):
        # Get the related CommonInformationModel instance
        common_info = self.common_information
        super().delete(*args, **kwargs)
        common_info.calculate_total_all_products()



# CommonAdditionalPaymentModel for shared additional fields
class CommonAdditionalPaymentModelMixins(models.Model):
    class Meta:
        abstract = True
        # This model is abstract, meaning it won't create a table in the database
        # but can be inherited by other models to share common fields or methods.
    common_information = models.ForeignKey(CommonInformationModelMixins, on_delete=models.CASCADE, related_name='additional_payments', verbose_name='ຂໍ້ມູນທົ່ວໄປ')
    total_all_product_ref = models.DecimalField(max_digits=10, decimal_places=2, default=Decimal('0.00'), editable=False, blank=True, null=True, verbose_name='ລາຄາລວມທັງໝົດ')

    it_service_percent = models.DecimalField(max_digits=3, decimal_places=0, default=Decimal('0'), verbose_name='ຄ່າບໍລິການ IT (%)')
    it_service_output = models.DecimalField(max_digits=10, decimal_places=2, default=Decimal('0.00'), editable=False, blank=True, null=True, verbose_name='ລາຄາບໍລິການ IT')

    vat_percent = models.DecimalField(max_digits=3, decimal_places=0, default=Decimal('0'), verbose_name='VAT (%)')
    vat_output = models.DecimalField(max_digits=10, decimal_places=2, default=Decimal('0.00'), editable=False, blank=True, null=True, verbose_name='VAT')

    exchange_rate = models.DecimalField(max_digits=10, decimal_places=0, default=Decimal('0'), verbose_name='ອັດຕາແລກປ່ຽນ')
    exchange_rate_output = models.DecimalField(max_digits=20, decimal_places=0, default=Decimal('0'), editable=False, blank=True, null=True, verbose_name='ອັດຕາແລກປ່ຽນ (ກິບ)')

    grand_total = models.DecimalField(max_digits=20, decimal_places=0, default=Decimal('0.00'), editable=False, blank=True, null=True, verbose_name='ລາຄາລວມທັງໝົດ (ທັງໝົດ)')

    # Recalculate all outputs base on the total_all_products
    def save(self, *args, **kwargs):
        if self.common_information and self.common_information.total_all_products is not None:
            self.total_all_product_ref = self.common_information.total_all_products
        else:
            self.total_all_product_ref = Decimal('0.00')
        base_amount = self.total_all_product_ref

        # Calculate IT service output
        if self.it_service_percent is not None:
            self.it_service_output = base_amount * (Decimal(self.it_service_percent) / Decimal('100'))
        else:
            self.it_service_output = Decimal('0.00')
        base_amount += self.it_service_output

        # Calculate VAT output
        if self.vat_percent is not None:
            self.vat_output = base_amount * (Decimal(self.vat_percent) / Decimal('100'))
        else:
            self.vat_output = Decimal('0.00')
        base_amount += self.vat_output

        # Calculate Exchange rate output
        if self.exchange_rate is not None:
            self.exchange_rate_output = base_amount * (Decimal(self.exchange_rate))
        else:
            self.exchange_rate_output = Decimal('0.00')
        
        # Calculate Grand total
        self.grand_total = base_amount
        super().save(*args, **kwargs)