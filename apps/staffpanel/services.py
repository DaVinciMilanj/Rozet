"""
کارهایی که از تابلو روی سفارش انجام می‌شود.

هر تابع:

* سفارش را **قفل‌شده** می‌خواند (``select_for_update``) و نسخه‌اش را با
  نسخه‌ای که کاربر دیده مقایسه می‌کند. دو نفر در آشپزخانه ممکن است
  همزمان روی یک کارت بزنند؛ بدون این، دومی بی‌صدا کار اولی را پاک
  می‌کند. نسخه‌ی کهنه ``Conflict`` می‌دهد و تابلو خودش تازه می‌شود.
* هر تغییر را در ``OrderStatusHistory`` ثبت می‌کند — با نام کسی که زد.

دسترسی **اینجا** بررسی نمی‌شود؛ ویو پیش از صدا زدن با ``can()`` سنجیده.
این ماژول فقط قواعد خودِ سفارش را می‌داند.
"""

from django.db import transaction
from django.utils import timezone

from apps.common.money import format_toman, toman_to_rial
from apps.common.text import parse_int
from apps.custom_cake.models import RequestStatus
from apps.orders.admin import log_status, stamp_fulfillment
from apps.orders.models import (FulfillmentStatus, Order, OrderItemKind,
                                OrderStatusHistory, PaymentStatus)
from apps.payments.models import Gateway, Payment, PaymentKind, PaymentState

SETTLE_CHANNELS = {
    'cash': Gateway.CASH,
    'card': Gateway.CARD,
    'transfer': Gateway.TRANSFER,
}


class ActionError(Exception):
    status = 400


class Conflict(ActionError):
    status = 409


class NotFound(ActionError):
    status = 404


def _locked(code, version):
    order = Order.objects.select_for_update().filter(code=code).first()
    if order is None:
        raise NotFound('سفارش پیدا نشد.')
    if version is not None and order.version != version:
        raise Conflict('این سفارش همین حالا از جای دیگری تغییر کرد؛ '
                       'تابلو تازه شد، دوباره نگاه کنید.')
    return order


def _bump(order, fields):
    order.version += 1
    order.save(update_fields=[*fields, 'version', 'updated_at'])


def _payment_status(order):
    if order.paid_rial <= 0:
        return PaymentStatus.UNPAID
    if order.paid_rial >= order.grand_total_rial:
        return PaymentStatus.PAID
    return PaymentStatus.DEPOSIT


# ═══════════════════════════════════════════════════════════════════
#  وضعیت آماده‌سازی
# ═══════════════════════════════════════════════════════════════════

@transaction.atomic
def advance(code, version, target, user):
    """
    گام بعد — دکمه‌ی اصلی کارت.

    ``target`` همان گامی است که روی دکمه دیده شده. اگر دیگر گام بعد
    نیست (کسی زودتر زده)، کار انجام نمی‌شود — وگرنه دو ضربه‌ی همزمان
    سفارش را دو پله جلو می‌برد.
    """
    order = _locked(code, version)
    if order.next_status is None or target != order.next_status:
        raise Conflict('این گام دیگر برای این سفارش معتبر نیست.')
    old = order.fulfillment_status
    order.fulfillment_status = target
    stamp_fulfillment(order, target)
    _bump(order, ['fulfillment_status', 'ready_at', 'delivered_at'])
    log_status(order, OrderStatusHistory.Field.FULFILLMENT, old, target, user,
               note='از تابلو')
    return order


@transaction.atomic
def step_back(code, version, user):
    """
    «برگرد» — فقط مدیر.

    زمانِ رسمیِ گامی که پس گرفته می‌شود هم پاک می‌شود؛ سفارشی که به
    «در حال پخت» برگشته نباید «آماده شد ساعت ۱۰» داشته باشد.
    """
    order = _locked(code, version)
    previous = order.previous_status
    if previous is None:
        raise ActionError('این سفارش گام قبلی ندارد.')
    old = order.fulfillment_status
    if old == FulfillmentStatus.DELIVERED:
        order.delivered_at = None
    elif old == FulfillmentStatus.READY:
        order.ready_at = None
    order.fulfillment_status = previous
    _bump(order, ['fulfillment_status', 'ready_at', 'delivered_at'])
    log_status(order, OrderStatusHistory.Field.FULFILLMENT, old, previous, user,
               reverse=True, note='از تابلو')
    return order


@transaction.atomic
def cancel(code, version, reason, user):
    """
    لغو سفارش — فقط مدیر، و فقط پیش از تحویل.

    سفارش حذف نمی‌شود (سند مالی است)؛ لغو می‌شود و از تابلو کنار
    می‌رود. اگر پولی گرفته شده، برگرداندنش کار جداگانه‌ای است و پیامش
    به مدیر داده می‌شود.
    """
    reason = str(reason or '').strip()
    if len(reason) < 3:
        raise ActionError('دلیل لغو را بنویسید.')
    order = _locked(code, version)
    if not order.can_move_to(FulfillmentStatus.CANCELED):
        raise ActionError('سفارش تحویل‌شده یا لغوشده را نمی‌شود لغو کرد.')
    old = order.fulfillment_status
    order.fulfillment_status = FulfillmentStatus.CANCELED
    order.canceled_at = timezone.now()
    order.canceled_by = user
    order.cancel_reason = reason[:200]
    _bump(order, ['fulfillment_status', 'canceled_at', 'canceled_by', 'cancel_reason'])
    log_status(order, OrderStatusHistory.Field.FULFILLMENT, old,
               FulfillmentStatus.CANCELED, user, note=reason[:200])
    # درخواست کیک اختصاصیِ پشت این سفارش هم لغو است.
    order.cake_requests.update(status=RequestStatus.CANCELED)
    return order


# ═══════════════════════════════════════════════════════════════════
#  پول
# ═══════════════════════════════════════════════════════════════════

@transaction.atomic
def settle(code, version, channel, user):
    """
    ثبت دریافت مانده هنگام تحویل — فقط مدیر.

    یک ``Payment`` واقعی ساخته می‌شود با نام کسی که پول را گرفته، نه
    فقط عوض‌شدن یک عدد؛ آخر شب صندوق باید با همین جدول جور دربیاید.
    """
    gateway = SETTLE_CHANNELS.get(channel)
    if gateway is None:
        raise ActionError('روش دریافت را انتخاب کنید.')
    order = _locked(code, version)
    if order.fulfillment_status == FulfillmentStatus.CANCELED:
        raise ActionError('سفارش لغو شده است.')
    amount = order.remaining_rial
    if amount <= 0:
        raise ActionError('مانده‌ای برای دریافت نیست.')

    Payment.objects.create(
        order=order, gateway=gateway, kind=PaymentKind.SETTLEMENT,
        amount_rial=amount, status=PaymentState.SUCCEEDED,
        paid_at=timezone.now(), recorded_by=user, note='ثبت از تابلو')

    old = order.payment_status
    order.paid_rial += amount
    order.payment_status = _payment_status(order)
    _bump(order, ['paid_rial', 'payment_status'])
    log_status(order, OrderStatusHistory.Field.PAYMENT, old, order.payment_status, user,
               note=f'دریافت {format_toman(amount)} تومان — {gateway.label}')
    return order


@transaction.atomic
def quote(code, version, price_toman, user):
    """
    قیمت نهایی کیک اختصاصی — فقط مدیر.

    تا این لحظه جمع سفارش برآورد است (سقف بازه‌ی ویزارد). با ثبت قیمت،
    هم درخواست کیک و هم جمع سفارش عوض می‌شود، و وضعیت پرداخت از نو
    حساب می‌شود — بیعانه‌ی گرفته‌شده از قیمت کم می‌شود نه از برآورد.
    """
    raw = str(price_toman if price_toman is not None else '')
    for separator in (',', '٬', '،', ' ', '‌'):
        raw = raw.replace(separator, '')
    toman = parse_int(raw)
    if toman is None:
        raise ActionError('قیمت را به تومان وارد کنید.')
    price = toman_to_rial(toman)
    if price <= 0:
        raise ActionError('قیمت باید بیشتر از صفر باشد.')

    order = _locked(code, version)
    if order.fulfillment_status == FulfillmentStatus.CANCELED:
        raise ActionError('سفارش لغو شده است.')
    items = list(order.items.select_related('custom_cake'))
    if not items or any(item.kind != OrderItemKind.CUSTOM or item.custom_cake is None
                        for item in items):
        raise ActionError('قیمت نهایی فقط برای سفارش کیک اختصاصی است.')
    if price < order.paid_rial:
        raise ActionError('قیمت نهایی از مبلغ پرداخت‌شده کمتر است.')

    # سفارش کیک اختصاصی یک قلم دارد؛ قیمت روی همان می‌نشیند.
    item = items[0]
    item.unit_price_rial = price // item.quantity
    item.line_total_rial = price
    item.save(update_fields=['unit_price_rial', 'line_total_rial'])
    cake = item.custom_cake
    cake.quoted_price_rial = price
    cake.reviewed_by = user
    cake.save(update_fields=['quoted_price_rial', 'reviewed_by', 'updated_at'])

    old = order.payment_status
    order.items_total_rial = price
    order.grand_total_rial = (price - order.discount_rial + order.delivery_fee_rial
                              + order.gift_wrap_rial + order.vat_rial)
    order.payment_status = _payment_status(order)
    _bump(order, ['items_total_rial', 'grand_total_rial', 'payment_status'])
    log_status(order, OrderStatusHistory.Field.PAYMENT, old, order.payment_status, user,
               note=f'قیمت نهایی: {format_toman(price)} تومان')
    return order


# ═══════════════════════════════════════════════════════════════════
#  یادداشت
# ═══════════════════════════════════════════════════════════════════

def save_note(code, text):
    """
    یادداشت داخلی — نسخه را بالا نمی‌برد.

    یادداشت با وضعیت تداخل ندارد: اگر کسی همزمان «آماده شد» زده باشد،
    یادداشت نباید به خاطرش رد شود.
    """
    updated = Order.objects.filter(code=code).update(
        staff_note=str(text or '').strip()[:1000], updated_at=timezone.now())
    if not updated:
        raise NotFound('سفارش پیدا نشد.')
