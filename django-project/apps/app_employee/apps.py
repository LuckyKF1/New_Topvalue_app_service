from django.apps import AppConfig


# make sure to update AppClassName and App name
class AppEmployeeConfig(AppConfig):
    default_auto_field = "django.db.models.BigAutoField"
    name = 'apps.app_employee'
    verbose_name = 'ຈັດການພະນັກງານ'
    label = 'app_employee'
