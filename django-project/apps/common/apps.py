from django.apps import AppConfig


# make sure to update AppClassName and App name
class CommonConfig(AppConfig):
    default_auto_field = "django.db.models.BigAutoField"
    name = 'apps.common'
    verbose_name = 'ຂໍ້ມູນທົ່ວໄປ'
    label = 'common'

    def ready(self):
        import apps.common.signals