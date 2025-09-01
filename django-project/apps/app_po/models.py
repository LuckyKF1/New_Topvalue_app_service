# coding=utf-8
from django.db import models
from django.conf import settings
from decimal import Decimal
from django.db.models import Sum
from django.core.exceptions import ValidationError

# Import external models
from apps.app_customers.models import CustomersModel
from apps.app_employee.models import EmployeesModel
from apps.app_quotations.models import QuotationInformationModel
from apps.app_invoices.models import InvoiceModel


# ----------------------------
# Purchase Order ID Generator
# ----------------------------
class PoIdGeneratorModel(models.Model):
    po_number_generator = models.BigIntegerField(default=0)

    class Meta:
        verbose_name = 'PO Number Generator'
        verbose_name_plural = 'PO Number Generators'


# ----------------------------
# Approver List
# ----------------------------
class ApprovedPOModel(models.Model):
    name = models.CharField(max_length=30, verbose_name='ຊື່')
    last_name = models.CharField(max_length=30, verbose_name='ນາມສະກຸນ')
    position = models.CharField(max_length=50,  verbose_name='ຕຳແຫນ່ງ')
    note = models.TextField(blank=True, null=True, verbose_name='ຫມາຍເຫດ')

    class Meta:
        verbose_name = 'ຜູ້ອະນຸມັດໃບສັ່ງຊື້'
        verbose_name_plural = 'ຜູ້ອະນຸມັດໃບສັ່ງຊື້'

    def __str__(self):
        return f"{self.name} {self.last_name} - {self.position}"


# ----------------------------
# Main Purchase Order
# ----------------------------
class PurchaseOrderModel(models.Model):
    class PoStatus(models.TextChoices):
        PENDING = 'pending', 'ລໍຖ້າອະນຸມັດ'
        COMPLETED = 'completed', 'ສຳເລັດ'
        REJECTED = 'rejected', 'ປະຕິເສດ'
        CANCELLED = 'cancelled', 'ຍົກເລີກ'
        BANNED = 'banned', 'ຖືກລະງັບ'

    po_id = models.CharField(max_length=20, unique=True, verbose_name='ລະຫັດໃບສັ່ງຊື້')
    customer = models.ForeignKey(
        CustomersModel,
        on_delete=models.CASCADE,
        related_name='purchase_orders',
        verbose_name='ລູກຄ້າ',
        null=True,
        blank=True
    )
    quotation = models.OneToOneField(
        QuotationInformationModel,
        on_delete=models.CASCADE,
        related_name='purchase_order',
        verbose_name='ໃບສະເຫນີລາຄາ'
    )
    invoice = models.OneToOneField(
        InvoiceModel,
        on_delete=models.CASCADE,
        related_name='purchase_order',
        verbose_name='ໃບເກັບເງິນ',
        blank=True,
        null=True
    )
    created_by = models.ForeignKey(
        EmployeesModel,
        on_delete=models.CASCADE,
        related_name='purchase_orders',
        verbose_name='ພະນັກງານຮັບຜິດຊອບ'
    )
    approved_by = models.ForeignKey(
        ApprovedPOModel,
        on_delete=models.SET_NULL,
        blank=True,
        null=True,
        related_name='approved_pos',
        verbose_name='ອະນຸມັດໂດຍ'
    )
    start_date = models.DateField(verbose_name='ວັນທີ່ເລີ່ມຕົ້ນ')
    end_date = models.DateField(verbose_name='ວັນທີ່ສິ້ນສຸດ')
    status = models.CharField(
        max_length=20,
        choices=PoStatus.choices,
        default=PoStatus.PENDING,
        verbose_name='ສະຖານະ'
    )
    approved_po = models.FileField(
        upload_to='approved_po/',
        blank=True,
        null=True,
        verbose_name='ອະນຸມັດໃບສັ່ງຊື້'
    )
    total_all_products = models.DecimalField(
        max_digits=12,
        decimal_places=2,
        default=Decimal('0.00'),
        editable=False,
        verbose_name='ລາຄາລວມທັງໝົດ'
    )

    class Meta:
        verbose_name = 'ໃບສັ່ງຊື້'
        verbose_name_plural = 'ໃບສັ່ງຊື້'
        ordering = ['-po_id']

    def clean(self):
        super().clean()
        if self.start_date and self.end_date and self.start_date >= self.end_date:
            raise ValidationError({'end_date': 'ວັນສິ້ນສຸດຕ້ອງຫຼາຍກວ່າວັນເລີ່ມ'})

    def __str__(self):
        customer = self.quotation.customer.company_name if self.quotation and self.quotation.customer else 'ບໍ່ມີລູກຄ້າ'
        return f"PO {self.po_id} - {customer}"

    def calculate_total_all_products(self):
        total_sum = self.items.aggregate(total=Sum('total_one_product'))['total']
        if total_sum is None:
            total_sum = Decimal('0.00')

        if self.total_all_products != total_sum:
            self.total_all_products = total_sum
            super(PurchaseOrderModel, self).save(update_fields=['total_all_products'])

# ----------------------------
# Purchase Order Items
# ----------------------------
class PurchaseOrderItemsModel(models.Model):
    purchase_order = models.ForeignKey(
        PurchaseOrderModel,
        on_delete=models.CASCADE,
        related_name='items',
        verbose_name='ໃບສັ່ງຊື້'
    )

    product_name = models.CharField(max_length=255, verbose_name='ຊື່ສິນຄ້າ')
    price = models.DecimalField(max_digits=12, decimal_places=2, default=Decimal('0.00'), verbose_name='ລາຄາ')
    qty = models.PositiveIntegerField(default=1, verbose_name='ຈຳນວນ')
    period = models.PositiveIntegerField(default=12, verbose_name='ລະດັບເວລາ (ເດືອນ)')
    total_one_product = models.DecimalField(
        max_digits=12,
        decimal_places=2,
        default=Decimal('0.00'),
        editable=False,
        verbose_name='ລາຄາລວມ'
    )

    class Meta:
        verbose_name = 'ລາຍການໃນໃບສັ່ງຊື້'
        verbose_name_plural = 'ລາຍການໃນໃບສັ່ງຊື້'

    def save(self, *args, **kwargs):
        if self.price is not None and self.qty is not None and self.period is not None:
            self.total_one_product = self.price * self.qty * self.period
        else:
            self.total_one_product = Decimal('0.00')
        super().save(*args, **kwargs)
        self.purchase_order.calculate_total_all_products()
    def delete(self, *args, **kwargs):
        common_info = self.purchase_order
        super().delete(*args, **kwargs)
        common_info.calculate_total_all_products()

    def __str__(self):
        return f"{self.product_name} ({self.qty} x {self.price})"
