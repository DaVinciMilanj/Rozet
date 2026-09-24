from django.apps import AppConfig


class CommonConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'apps.common'
    label = 'common'
    verbose_name = 'مشترک'

    def ready(self):
        # فرمت‌های افزودنی (HEIC/HEIF) باید پیش از اولین اعتبارسنجی فرم
        # ثبت شوند، وگرنه عکس آیفون «تصویر نامعتبر» شمرده می‌شود.
        from . import images, signals
        images.register_openers()
        signals.connect()
