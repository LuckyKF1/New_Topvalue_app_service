from django.db.models.signals import pre_save, post_save, post_delete
from django.dispatch import receiver
from django.db import transaction
from .models import InvoiceModel, GenerateInvoiceNumber

PREFIX = 'INV'

# Auto Generate Invoice Number
@receiver(pre_save, sender=InvoiceModel)
def generate_invoice_number(sender, instance, **kwargs):
    if not instance.invoice_id:
        with transaction.atomic():
            generator, created = GenerateInvoiceNumber.objects.select_for_update().get_or_create(pk=1)
            generator.auto_invoice_number += 1
            generator.save()
            instance.invoice_id = f"{PREFIX}{generator.auto_invoice_number:07d}"