"""
درخواست کیک اختصاصی ← سفارش آشپزخانه.

تابلوی آشپزخانه فقط ``Order`` می‌خواند. درخواستی که بیعانه‌اش پرداخت
شده، باید همان لحظه روی تابلو بیاید — وگرنه کسی نمی‌فهمد کیکی سفارش
داده شده.

تا وقتی مدیر قیمت نهایی را از تابلو ثبت نکرده، جمع سفارش **برآورد**
است (سقف بازه‌ی ویزارد) و تابلو همین را با برچسب «برآورد» نشان می‌دهد.

این تابع از دو جا صدا زده می‌شود و باید از هر دو یک نتیجه بدهد:
    * ویزارد، وقتی درگاه همان‌جا «موفق» برمی‌گرداند (امروز: درگاه آزمایشی)
    * بازگشت از درگاه واقعی، وقتی وصل شد
پس تکرارش بی‌خطر است: درخواستی که سفارش دارد، سفارش دوم نمی‌سازد.
"""

from django.db import transaction
from django.db.models import Sum

from apps.orders.models import (DeliveryMethod, Order, OrderItem, OrderItemKind,
                                PaymentStatus, PayMethod)
from apps.payments.models import PaymentState

from .models import CakeMode, CustomCakeRequest, RequestStatus


def _item_name(cake):
    name = f'کیک اختصاصی {cake.flavor.label}'
    if cake.mode == CakeMode.PRINT:
        name += ' — با چاپ عکس'
    return name[:140]


@transaction.atomic
def to_order(cake):
    cake = (CustomCakeRequest.objects.select_for_update()
            .select_related('size', 'flavor').get(pk=cake.pk))
    if cake.order_id:
        return cake.order

    paid = (cake.payments.filter(status=PaymentState.SUCCEEDED)
            .aggregate(total=Sum('amount_rial'))['total'] or 0)
    total = cake.quoted_price_rial or cake.estimate_max_rial
    courier = bool(cake.address.strip())

    order = Order(
        user=cake.user,
        customer_name=cake.full_name[:120],
        customer_phone=cake.contact_phone,
        method=DeliveryMethod.COURIER if courier else DeliveryMethod.PICKUP,
        address_snapshot=({'line': cake.address.strip()[:300],
                           'receiver_name': cake.full_name,
                           'receiver_phone': cake.contact_phone} if courier else {}),
        due_date=cake.event_date,
        pay_method=PayMethod.ONLINE,
        items_total_rial=total,
        grand_total_rial=total,
        paid_rial=paid,
        payment_status=(PaymentStatus.UNPAID if paid <= 0 else
                        PaymentStatus.PAID if paid >= total else PaymentStatus.DEPOSIT),
        allergy_note=cake.allergy_note,
        customer_note=(f'شماره دوم: {cake.contact_phone_alt}'
                       if cake.contact_phone_alt else ''),
    )
    # سیگنال اعلان از همین می‌فهمد زنگ «کیک اختصاصی» است نه سفارش عادی.
    order._from_cake = True
    order.save()

    OrderItem.objects.create(
        order=order, kind=OrderItemKind.CUSTOM, custom_cake=cake,
        name=_item_name(cake),
        size_label=cake.size.label[:80],
        flavor_label=cake.flavor.label[:80],
        message_on_cake=cake.message_on_cake,
        quantity=1, unit_price_rial=total, line_total_rial=total)

    cake.order = order
    cake.status = RequestStatus.CONVERTED
    cake.save(update_fields=['order', 'status', 'updated_at'])
    return order
