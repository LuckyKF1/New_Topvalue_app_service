# coding=utf-8
from django.db import models
from django.utils import timezone
from django.core.exceptions import ValidationError
# Import external models
from apps.app_customers.models import CustomersModel, CustomerTenantModel
from apps.app_employee.models import EmployeesModel
from apps.app_quotations.models import QuotationInformationModel
from apps.app_invoices.models import InvoiceModel
from apps.app_po.models import PurchaseOrderModel, ApprovedPOModel

# Generate Contract Number
class GenerateContractNumber(models.Model):
    auto_generate_number = models.BigIntegerField(default=0)



# Contract Model Here
class ContractsModel(models.Model):
    class ContractStatus(models.TextChoices):
        DRAFT = 'Draft','ຮ່າງ'
        ACTIVE = 'Active', 'ກຳລັງໃຊ້ງານ'
        EXPIRED = 'Expired', 'ຫມົດອາຍຸການນຳໃຊ້'
        BANNED = 'Banned', 'ລະງັບ'

    contract_id = models.CharField(max_length=20, primary_key=True)
    customer = models.ForeignKey(
        CustomersModel,
        on_delete=models.CASCADE,
        related_name='contract_customer',
        verbose_name='ລູກຄ້າ'
    )
    created_by = models.ForeignKey(
        EmployeesModel,
        on_delete=models.CASCADE,
        related_name='contract_employee',
        verbose_name='ພະນັກງານຮັບຜິດຊອບ'
    )
    quotation = models.OneToOneField(
        QuotationInformationModel,
        on_delete=models.CASCADE,
        related_name= 'contract_quotation',
        verbose_name= 'ໃບສະເຫນີລາຄາທີ່ກ່ຽວຂ້ອງ'
    )
    invoice = models.OneToOneField(
        InvoiceModel,
        on_delete=models.CASCADE,
        related_name='contract_invoice',
        verbose_name='ໃບເກັບເງິນທີ່ກ່ຽວຂ້ອງ'
    )
    po = models.OneToOneField(
        PurchaseOrderModel,
        on_delete=models.CASCADE,
        related_name='contract_po',
        verbose_name='ໃບສັ່ງຊື້ທີ່ກ່ຽວຂ້ອງ'
    )
    start_contract = models.DateField(
        verbose_name= 'ວັນທີອອກສັນຍາ'
    )
    end_contract = models.DateField(
        verbose_name='ວັນທີຫມົດສັນຍາ'
    )
    status = models.CharField(
        max_length=30,
        choices=ContractStatus.choices,
        default=ContractStatus.DRAFT,
        verbose_name='ສະຖານະຂອງສັນຍາ'
    )

    class Meta:
        verbose_name = 'ຈັດການສັນຍາ'
        verbose_name_plural = 'ຈັດການສັນຍາ'

    def __str__(self):
        return f"{self.contract_id} - ລູກຄ້າ  {self.customer.company_name}"
    
    def save(self, *args, **kwargs):
        today = timezone.now().date()
        if self.end_contract < today:
            self.status = self.ContractStatus.EXPIRED
        elif self.start_contract <= today <= self.end_contract:
            self.status = self.ContractStatus.ACTIVE
        else:
            self.status = self.ContractStatus.DRAFT
        super().save(*args, **kwargs)
    def clean(self):
        if self.start_contract and self.end_contract:
            if self.end_contract <= self.start_contract:
                raise ValidationError("ວັນທີຫມົດສັນຍາຕ້ອງນ້ອຍຫາວັນທີອອກສັນຍາ")