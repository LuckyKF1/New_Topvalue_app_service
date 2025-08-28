from django.db import models
from decimal import Decimal

# Import Models
from apps.common.mixins import (
    CommonInformationModelMixins,
    CommonItemsModelMixins,
    CommonAdditionalPaymentModelMixins
)
from apps.app_customers.models import CustomersModel
from apps.app_employee.models import EmployeesModel

# Generate ID of Quotation
class GenerateQuotationID(models.Model):
    qotation_id_generator = models.BigIntegerField(default=0)

# Main Quotation Model
class QuotationInformationModel(CommonInformationModelMixins):
    """
    Main Model of Quotation
    - Using Fields and method from Mixins
    - total_all_product will calculate from items
    """
    quotation_id = models.CharField(max_length=20, primary_key=True)
    start_date = models.DateField(verbose_name='ວັນທີອອກ')
    end_date = models.DateField(verbose_name='ວັນທີ່ສິ້ນສຸດ')
    upload_signatured_quo = models.FileField(upload_to='quotation_docs/', blank=True, null=True, verbose_name='ໃບສະເຫນີລາຄາທີ່ເຊັນຮັບຮອງແລ້ວ')
    customer_po = models.FileField(upload_to='quotation_docs/', blank=True, null=True, verbose_name='ໃບສັ່ງຊື້ຂອງລູກຄ້າ')

    class Meta:
        verbose_name = 'ໃບສະເຫນີລາຄາ'
        verbose_name_plural = 'ໃບສະເຫນີລາຄາ'
        ordering = ['-end_date']
    def __str__(self):
        return f"ໃບສະເຫນີລາຄາ {self.quotation_id} - ລູກຄ້າ {self.customer.company_name} - ຜູ້ຕິດຕໍ່ {self.customer.contact_person_name}"

# Items Model
class QuotationItemsModel(CommonItemsModelMixins):
    """
    Items Model for quotation
    - total_one_product will auto calculate from price * qty * period
    - when save/delete will triger calculate total_all_products of parent
    """
    common_information = models.ForeignKey(
        'QuotationInformationModel',
        on_delete=models.CASCADE,
        related_name='items'
    )

# Additional Expenses Model
class AdditionalExpensesModel(CommonAdditionalPaymentModelMixins):
    """
    Model for additional expenses
    - grand_total, it_service, exchange_rate will auto calculate
    """
    common_information = models.ForeignKey(
        'QuotationInformationModel',
        on_delete=models.CASCADE,
        related_name='additional_payments'
    )