from django.db.models.signals import pre_save, post_save, post_delete
from django.dispatch import receiver
from django.db import transaction
from .models import QuotationInformationModel, QuotationItemsModel, AdditionalExpensesModel, GenerateQuotationID

PREFIX = "QUO"

# Update total_all_products when save/delete item
@receiver([post_save, post_delete], sender=QuotationItemsModel)
def update_total_all_product(sender, instance, **kwargs):
    quotation = instance.common_information
    if quotation.pk:
        quotation.calculate_total_all_products()

# Auto-Generate quotation_ID before save
@receiver(pre_save, sender=QuotationInformationModel)
def quotation_id_generator(sender, instance, **kwargs):
    if not instance.quotation_id:
        with transaction.atomic():
            generator, created = GenerateQuotationID.objects.select_for_update().get_or_create(pk=1)
            generator.qotation_id_generator += 1
            generator.save()
            instance.quotation_id = f"{PREFIX}{generator.qotation_id_generator:07d}"
