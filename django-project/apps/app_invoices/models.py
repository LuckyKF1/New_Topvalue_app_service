# coding=utf-8
from django.db import models
from django.conf import settings
from decimal import Decimal
from apps.app_quotations.models import QuotationInformationModel
from apps.app_employee.models import EmployeesModel
from apps.app_customers.models import CustomersModel


#Generate invoice number
class GenerateInvoiceNumber(models.Model):
    auto_invoice_number = models.BigIntegerField(default=0)

# Main Invoice Models
class InvoiceModel(models.Model):
    class InvoiceStatus(models.TextChoices):
        PENDING = 'pending','ກຳລັງລໍຖ້າອະນຸມັດ'
        UNPAUD = 'unpaid', 'ຍັງບໍ່ໄດ້ຈ່າຍ'
        PAID = 'paid', 'ຈ່າຍແລ້ວ'
        REJECTED = 'rejected', 'ປະຕິເສດ'
        CANCELLED = 'cancelled', 'ຍົກເລີກ'

    invoice_id = models.CharField(max_length=20, unique=True, verbose_name='ລະຫັດໃບເກັບເງິນ')
    quotation = models.OneToOneField(
        QuotationInformationModel,
        on_delete=models.CASCADE,
        related_name='invoice',
        verbose_name='ໃບສະເຫນີລາຄາ'
    )
    issue_date = models.DateField(verbose_name='ວັນທີອອກໃບເກັບເງິນ')
    due_date = models.DateField(verbose_name='ວັນທີຫມົດອາຍຸ')
    status = models.CharField(
        max_length=20,
        choices=InvoiceStatus.choices,
        default=InvoiceStatus.PENDING,
        verbose_name='ສະຖານະ'
    )
    created_by = models.ForeignKey(
        EmployeesModel,
        on_delete=models.CASCADE,
        verbose_name='ພະນັກງານຮັບຜິດຊອບ',
        blank=True,
        null=True
    )
    invoice_signatured = models.FileField(upload_to='invoice_docs/', blank=True, null=True, verbose_name='ໃບເກັບເງິນທີ່ຮັບຮອງແລ້ວ ຫລື ໃບສັ່ງຊື້ຈາກລູກຄ້າ')
    customer_payment = models.FileField(upload_to='invoice_docs/', blank=True, null=True, verbose_name='ຫລັກຖານການຈ່າຍເງິນຂອງລູກຄ້າ')

    class Meta:
        verbose_name = 'ການຈັດການ ໃບເກັບເງິນ'
        verbose_name_plural = 'ການຈັດການ ໃບເກັບເງິນ'
        ordering = ['-due_date']

    def __str__(self):
        return f"ເລກໃບເກັບເງິນ: {self.invoice_id} - ເລກໃບສະເຫນີລາຄາ: {self.quotation.quotation_id} - ບໍລິສັດ {self.quotation.customer.company_name} - ວັນທີອອກ {self.issue_date} - ວັນທີ່ຫມົດອາຍຸ {self.due_date} - ສະຖານະ {self.status}"
    
