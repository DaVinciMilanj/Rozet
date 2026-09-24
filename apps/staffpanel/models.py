"""
اعلان‌های پنل کارکنان.

منبع در تمپلیت:
    admin/orders/orders.js   زنگ اعلان · شمارنده‌ی عنوان تب ·
                             اعلان گوشه‌ی صفحه که تا نزنند نمی‌رود
"""

from django.conf import settings
from django.db import models

from apps.common.models import TimeStampedModel


class NotificationKind(models.TextChoices):
    NEW_ORDER = 'new_order', 'سفارش جدید'
    NEW_CAKE_REQUEST = 'cake_request', 'درخواست کیک اختصاصی'
    PAYMENT = 'payment', 'پرداخت'
    OVERDUE = 'overdue', 'سفارش عقب‌افتاده'
    CANCELED = 'canceled', 'لغو سفارش'
    SYSTEM = 'system', 'سیستمی'


class StaffNotification(TimeStampedModel):
    """
    اعلان تابلو.

    ``target_roles`` یک رشته‌ی جداشده با کاماست، نه JSONField. دلیلش
    عملی است: ``target_roles__contains`` روی JSONField در SQLite
    پشتیبانی نمی‌شود و ``NotSupportedError`` می‌دهد — یعنی همان کوئری که
    روی پستگرس کار می‌کند، در محیط توسعه می‌شکند. برای مجموعه‌ی کوچک و
    ثابت سه نقش، رشته کافی است.
    """

    kind = models.CharField('نوع', max_length=16, choices=NotificationKind.choices,
                            default=NotificationKind.SYSTEM)
    title = models.CharField('عنوان', max_length=140)
    body = models.CharField('متن', max_length=300, blank=True)

    order = models.ForeignKey(
        'orders.Order', on_delete=models.CASCADE, null=True, blank=True,
        related_name='notifications', verbose_name='سفارش')
    cake_request = models.ForeignKey(
        'custom_cake.CustomCakeRequest', on_delete=models.CASCADE, null=True, blank=True,
        related_name='notifications', verbose_name='درخواست کیک')

    target_roles = models.CharField(
        'نقش‌های مخاطب', max_length=60, default='kitchen,manager',
        help_text='با کاما جدا کنید: kitchen,manager')

    is_urgent = models.BooleanField('فوری', default=False)

    # «دیده شد» به‌ازای هر کاربر. اگر یک ستون بولی روی خود اعلان
    # بود، اولین نفری که زنگ را باز می‌کرد آن را برای کل آشپزخانه
    # خاموش می‌کرد. M2M همین را بدون مدل واسط انجام می‌دهد.
    seen_by = models.ManyToManyField(
        settings.AUTH_USER_MODEL, blank=True,
        related_name='seen_notifications', verbose_name='دیده شده توسط')

    class Meta:
        verbose_name = 'اعلان پنل'
        verbose_name_plural = 'اعلان‌های پنل'
        ordering = ('-created_at',)
        indexes = [
            models.Index(fields=['-created_at', 'kind'], name='notif_recent_idx'),
        ]

    def __str__(self):
        return self.title

    @property
    def roles(self):
        return [role.strip() for role in self.target_roles.split(',') if role.strip()]

    def is_for(self, user):
        return user.role in self.roles
