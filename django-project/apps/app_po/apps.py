from django.apps import AppConfig


# make sure to update AppClassName and App name
class AppPoConfig(AppConfig):
    default_auto_field = "django.db.models.BigAutoField"
    name = 'apps.app_po'
    verbose_name = 'ຈັດການການສັ່ງຊື້'
    label = 'app_po'

    def ready(self):
        import apps.app_po.signals