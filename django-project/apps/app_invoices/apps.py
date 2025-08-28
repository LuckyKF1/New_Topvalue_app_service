from django.apps import AppConfig


# make sure to update AppClassName and App name
class AppInvoicesConfig(AppConfig):
    default_auto_field = "django.db.models.BigAutoField"
    name = 'apps.app_invoices'
    verbose_name = 'ແອັບຈັດການໃບເກັບເງິນ'
    label = 'app_invoices'