from django.apps import AppConfig


class CustomCakeConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'apps.custom_cake'
    label = 'custom_cake'
    verbose_name = 'کیک اختصاصی'
