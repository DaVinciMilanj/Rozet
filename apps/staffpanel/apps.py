from django.apps import AppConfig


class StaffPanelConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'apps.staffpanel'
    label = 'staffpanel'
    verbose_name = 'پنل کارکنان'

    def ready(self):
        from . import signals  # noqa: F401  (اعلان سفارش تازه)
