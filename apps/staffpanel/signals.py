"""
اعلان سفارش تازه برای زنگ تابلو.

سیگنال، نه صدا زدن از صفحه‌ی پرداخت: سفارش از سه جا ساخته می‌شود
(صفحه‌ی پرداخت، ویزارد کیک اختصاصی، پنل جنگو) و هر سه باید زنگ را به
صدا دربیاورند. ``post_save`` تنها جایی است که هر سه از آن رد می‌شوند.
"""

from django.db.models.signals import post_save
from django.dispatch import receiver

from apps.orders.models import Order

from .models import NotificationKind, StaffNotification


@receiver(post_save, sender=Order, dispatch_uid='staffpanel_new_order')
def notify_new_order(sender, instance, created, raw=False, **kwargs):
    if not created or raw:
        return
    custom = getattr(instance, '_from_cake', False)
    StaffNotification.objects.create(
        kind=NotificationKind.NEW_CAKE_REQUEST if custom else NotificationKind.NEW_ORDER,
        title=f"{'کیک اختصاصی' if custom else 'سفارش تازه'} — {instance.customer_name}",
        order=instance,
        target_roles='kitchen,manager',
    )
