# from django.db.models.signals import post_save, post_delete
# from django.dispatch import receiver
# from decimal import Decimal

# from .mixins import CommonInformationModelMixins, CommonItemsModelMixins, CommonAdditionalPaymentModelMixins

# @receiver([post_save, post_delete], sender=CommonItemsModelMixins)
# def update_total_all_products(sender, instance, **kwargs):
#     """
#     update total_all_products of CommonInformationModel
#     and Even recalculate of CommonAdditionalPaymentModewl Everytime when CommonItemModel save or delete
#     """
#     common_info = instance.common_information
#     common_info.calculate_total_all_products()

#     # Update additional payments if any updated
#     additional_payment = common_info.additional_payments.first()
#     if additional_payment:
#         additional_payment.save()

# @receiver([post_save, post_delete], sender=CommonAdditionalPaymentModelMixins)
# def recalculate_additional_payment(sender, instance, **kwargs):
#     """
#     event any update CommonAdditionalPaymentModel will recalculate all
#     """
#     pass
