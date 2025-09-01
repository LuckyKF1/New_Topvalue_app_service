from django.db.models.signals import pre_save, post_save, post_delete
from django.dispatch import receiver
from django.db import transaction
from .models import PoIdGeneratorModel, PurchaseOrderModel, PurchaseOrderItemsModel

PREFIX = 'PO'

# Update total_all_product when save/delete item
@receiver([post_save, post_delete], sender=PurchaseOrderItemsModel)
def update_total_all_product(sender, instance, **kwargs):
    po = instance.purchase_order
    if po.pk:
        po.calculate_total_all_products()


# Auto-Generate po_id before save
@receiver(pre_save, sender=PurchaseOrderModel)
def po_id_generator(sender, instance, **kwargs):
    if not instance.pk and not instance.po_id:  # เช็คว่าเป็นการ create
        with transaction.atomic():
            generator, created = PoIdGeneratorModel.objects.select_for_update().get_or_create(pk=1)
            generator.po_number_generator += 1
            generator.save()
            instance.po_id = f"{PREFIX}-{generator.po_number_generator:07d}"
