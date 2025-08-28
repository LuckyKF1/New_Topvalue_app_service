from django.apps import AppConfig


# make sure to update AppClassName and App name
class AppQuotationsSmallConfig(AppConfig):
    default_auto_field = "django.db.models.BigAutoField"
    name = 'apps.app_quotations'
    verbose_name = 'ການຈັດການໃບວະເຫນີລາຄາ'
    label = 'app_quotations'

    def ready(self):
        # Import Signals to Django register signals on app load
        import apps.app_quotations.signals