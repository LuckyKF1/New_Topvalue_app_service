from .models import ContractsModel, GenerateContractNumber
from django.dispatch import receiver
from django.db.models.signals import pre_save, post_save, post_delete
from django.db import transaction
from django.utils import timezone

# Text Prefix
PREFIX = 'TVS-CON'

# Auto Generate Contract Number
@receiver(pre_save, sender=ContractsModel)
def contract_id_generator(sender, instance, **kwargs):
    if not instance.contract_id:
        with transaction.atomic():
            generator, created = GenerateContractNumber.objects.select_for_update().get_or_create(pk=1)
            generator.auto_generate_number += 1
            generator.save()
            instance.contract_id = f"{PREFIX}{generator.auto_generate_number:07d}"

# Notification
@receiver([post_save, post_delete], sender=ContractsModel)
def notification_expired(sender, instance, **kwargs):
    pass