from django.apps import AppConfig


# make sure to update AppClassName and App name
class AppContractsConfig(AppConfig):
    default_auto_field = "django.db.models.BigAutoField"
    name = 'apps.app_contracts'
    verbose_name = 'ລະບົບການຈັດການສັນຍາຂອງລູກຄ້າ'
    label = 'app_contracts'

    def ready(self):
        import apps.app_contracts.signals