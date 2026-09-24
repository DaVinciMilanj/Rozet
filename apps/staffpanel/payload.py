"""
شکل داده‌ای که تابلو و صفحه‌ی جزئیات می‌خوانند.

جاوااسکریپت تمپلیت روی آرایه‌ی ``ORDERS`` در ``orders-data.js`` نوشته
شده بود. این ماژول دقیقاً همان شکل را از دیتابیس می‌سازد — همان کلیدها
(``who``، ``tel``، ``due``، ``time``، ``items[].spec``، ``refs``،
``print``…) — تا موتور تابلو دست‌نخورده بماند و فقط منبع داده عوض شود.

مبلغ‌ها تومانِ عددی‌اند (مثل تمپلیت)؛ تبدیل از ریال فقط همین‌جاست.
"""

from datetime import timedelta

from django.conf import settings
from django.db.models import Prefetch, Q
from django.templatetags.static import static
from django.urls import reverse
from django.utils import timezone

from apps.common.money import rial_to_toman
from apps.custom_cake.models import CakeImageKind, CustomCakeRequest
from apps.orders.models import (DeliveryMethod, FulfillmentStatus, Order,
                                OrderItemKind, OrderStatusHistory, PayMethod)
from apps.payments.models import PaymentState

from .models import StaffNotification

CUSTOM_PLACEHOLDER = 'assets/images/custom-cake.webp'
NO_IMAGE = 'assets/logo/rozet-icon.webp'

# یادداشت‌هایی که فقط «از کجا» را می‌گویند، نه «چرا» را؛ در تاریخچه
# نشان داده نمی‌شوند. دلیل لغو یا «برگشت چون…» نشان داده می‌شود.
SOURCE_NOTES = ('از پنل مدیریت', 'اکشن گروهی', 'از تابلو')

HISTORY_LABELS = {
    FulfillmentStatus.NEW: 'سفارش ثبت شد',
    FulfillmentStatus.BAKING: 'آماده‌سازی شروع شد',
    FulfillmentStatus.READY: 'آماده‌ی تحویل شد',
    FulfillmentStatus.DELIVERED: 'به مشتری تحویل شد',
    FulfillmentStatus.CANCELED: 'سفارش لغو شد',
}


# ═══════════════════════════════════════════════════════════════════
#  کوئری‌ها
# ═══════════════════════════════════════════════════════════════════

def _with_relations(queryset, history=False):
    """
    همه‌ی چیزی که کارت و برگه‌ی سفارش لازم دارند، با تعداد ثابتی کوئری.

    بدون این، هر کارت برای اقلامش، هر قلم برای مشخصاتش و هر کیک
    اختصاصی برای عکس‌ها و پرداخت‌هایش یک کوئری جدا می‌زد.
    """
    cakes = CustomCakeRequest.objects.select_related(
        'size', 'flavor', 'filling', 'coating', 'occasion'
    ).prefetch_related('images', 'payments')
    queryset = queryset.select_related('user', 'slot').prefetch_related(
        'items__specs',
        Prefetch('items__custom_cake', queryset=cakes),
        'payments',
    )
    if history:
        queryset = queryset.prefetch_related(Prefetch(
            'history', queryset=OrderStatusHistory.objects.select_related('changed_by')))
    return queryset


def board_orders():
    """
    سفارش‌های تابلو.

    همه‌ی سفارش‌های باز (از هر روزی — عقب‌افتاده‌ها هم باید بمانند) به‌علاوه‌ی
    تحویل‌شده‌های دیروز به بعد برای فیلتر «با تحویل‌شده‌ها». لغوشده‌ها
    روی تابلو نمی‌آیند؛ کاری روی آن‌ها نمانده.
    """
    since = timezone.localdate() - timedelta(days=1)
    queryset = (Order.objects
                .exclude(fulfillment_status=FulfillmentStatus.CANCELED)
                .filter(~Q(fulfillment_status=FulfillmentStatus.DELIVERED)
                        | Q(due_date__gte=since)))
    return list(_with_relations(queryset))


def find_order(code, history=True):
    return _with_relations(Order.objects.filter(code=code), history=history).first()


def unseen_notifications(user, level):
    """اعلان‌های سفارشی که این کاربر هنوز ندیده — زنگ تابلو."""
    return (StaffNotification.objects
            .filter(order__isnull=False, target_roles__contains=level,
                    created_at__gte=timezone.now() - timedelta(days=3))
            .exclude(order__fulfillment_status=FulfillmentStatus.CANCELED)
            .exclude(seen_by=user))


def unseen_codes(user, level):
    rows = unseen_notifications(user, level).values_list('order__code', flat=True)
    return list(dict.fromkeys(rows))       # یکتا، به ترتیب تازه‌ترین


# ═══════════════════════════════════════════════════════════════════
#  سفارش ← شکل تمپلیت
# ═══════════════════════════════════════════════════════════════════

def _iso(value):
    if value is None:
        return ''
    if hasattr(value, 'hour'):
        value = timezone.localtime(value)
        return value.date().isoformat()
    return value.isoformat()


def _where(order):
    if order.method == DeliveryMethod.PICKUP:
        cafe = settings.CAFE
        return f"{cafe['city']}، {cafe['address']} — شعبه‌ی {cafe['name']}"
    snap = order.address_snapshot or {}
    parts = [snap.get('city'), snap.get('district'), snap.get('line')]
    line = '، '.join(part for part in parts if part)
    if snap.get('plaque'):
        line += f"، پلاک {snap['plaque']}"
    if snap.get('unit'):
        line += f"، واحد {snap['unit']}"
    receiver = snap.get('receiver_name')
    if receiver and receiver != order.customer_name:
        line += f" — تحویل‌گیرنده: {receiver} {snap.get('receiver_phone', '')}"
    return line or 'نشانی ثبت نشده'


def _cakes(order):
    return [item.custom_cake for item in order.items.all()
            if item.kind == OrderItemKind.CUSTOM and item.custom_cake is not None]


def _pay_method(order):
    """
    «روش» در کادر پرداخت — از روی پرداخت‌های موفق، نه از انتخاب مشتری.

    پرداخت آزمایشی (بدون درگاه واقعی) صریحاً علامت می‌خورد: کسی که
    کیک را تحویل می‌دهد نباید آن را پول واقعی بداند.
    """
    payments = [p for p in order.payments.all() if p.status == PaymentState.SUCCEEDED]
    for cake in _cakes(order):
        payments += [p for p in cake.payments.all() if p.status == PaymentState.SUCCEEDED]
    if not payments:
        if order.pay_method == PayMethod.ONSITE:
            return 'پرداخت در محل'
        return 'آنلاین — پرداخت نشده'
    labels = []
    for payment in sorted(payments, key=lambda p: p.created_at):
        label = f'{payment.get_kind_display()} — {payment.get_gateway_display()}'
        if label not in labels:
            labels.append(label)
    return '، '.join(labels)


def _warn(order):
    bits = []
    if order.allergy_note.strip():
        bits.append(f'حساسیت: {order.allergy_note.strip()}')
    if order.customer_note.strip():
        bits.append(order.customer_note.strip())
    return ' — '.join(bits)


def _catalogue_item(item):
    spec = []
    if item.size_label:
        spec.append({'l': 'اندازه', 'v': item.size_label})
    if item.flavor_label:
        spec.append({'l': 'طعم و افزودنی', 'v': item.flavor_label})
    spec += [{'l': row.label, 'v': row.value} for row in item.specs.all()]
    return {
        'kind': 'catalogue',
        'n': item.name,
        's': item.size_label,
        'q': item.quantity,
        'p': rial_to_toman(item.unit_price_rial),
        'img': item.image.url if item.image else static(NO_IMAGE),
        'spec': spec,
        'write': item.message_on_cake,
    }


def _image_url(image):
    return reverse('custom_cake:image', args=[image.pk])


def _custom_item(item):
    cake = item.custom_cake
    size = cake.size
    spec = [{'l': 'اندازه', 'v': ' — '.join(x for x in (size.serves, size.approx_weight) if x)
             or size.label}]
    if cake.tiers > 1:
        spec.append({'l': 'طبقه', 'v': f'{cake.tiers} طبقه'})
    spec += [
        {'l': 'طعم کیک', 'v': cake.flavor.label},
        {'l': 'فیلینگ', 'v': cake.filling.label},
        {'l': 'روکش', 'v': cake.coating.label},
    ]
    if cake.color_theme:
        spec.append({'l': 'رنگ غالب', 'v': cake.color_theme})
    if cake.occasion_id:
        spec.append({'l': 'مناسبت', 'v': str(cake.occasion)})
    spec.append({'l': 'کد درخواست', 'v': cake.code})
    spec += [{'l': row.label, 'v': row.value} for row in item.specs.all()]

    images = sorted(cake.images.all(), key=lambda image: (image.sort_order, image.pk))
    refs = [_image_url(image) for image in images if image.kind == CakeImageKind.REFERENCE]
    prints = [_image_url(image) for image in images if image.kind == CakeImageKind.PRINT]

    data = {
        'kind': 'custom',
        'n': item.name,
        's': size.serves or size.label,
        'q': item.quantity,
        'p': rial_to_toman(item.unit_price_rial),
        'img': (refs or prints or [static(CUSTOM_PLACEHOLDER)])[0],
        'spec': spec,
        'write': item.message_on_cake or cake.message_on_cake,
        'refs': refs,
        'refNote': cake.design_note if refs else '',
    }
    if prints:
        data['print'] = prints[0]
        data['printNote'] = 'چاپ روی کاغذ خوراکی' + (
            f' — {cake.design_note}' if cake.design_note else '')
    return data


def _history(order):
    rows = []
    for entry in order.history.all():
        if entry.field == OrderStatusHistory.Field.FULFILLMENT:
            label = HISTORY_LABELS.get(entry.to_value, entry.to_value)
            if entry.is_reverse:
                label = f'برگشت به «{FulfillmentStatus(entry.to_value).label}»'
        else:
            label = entry.note or 'تغییر وضعیت پرداخت'
        if entry.field == OrderStatusHistory.Field.FULFILLMENT and entry.note \
                and entry.note not in SOURCE_NOTES:
            label += f' — {entry.note}'
        local = timezone.localtime(entry.changed_at)
        rows.append({
            'k': entry.to_value, 'l': label, 'd': local.date().isoformat(),
            't': local.strftime('%H:%M'),
            'by': (entry.changed_by.get_short_name() if entry.changed_by else ''),
        })
    # ثبت سفارش در جدول تاریخچه ردیف ندارد؛ زمانش خودِ placed_at است.
    placed = timezone.localtime(order.placed_at)
    return [{'k': 'new', 'l': HISTORY_LABELS[FulfillmentStatus.NEW],
             'd': placed.date().isoformat(), 't': placed.strftime('%H:%M'), 'by': ''}] + rows


def order_payload(order, history=False):
    cakes = _cakes(order)
    items = [(_custom_item(item) if item.kind == OrderItemKind.CUSTOM and item.custom_cake
              else _catalogue_item(item)) for item in order.items.all()]
    user = order.user
    data = {
        'code': order.code,
        'who': order.customer_name,
        'tel': order.customer_phone,
        'placed': _iso(order.placed_at),
        'due': _iso(order.due_date),
        'time': order.slot.start_time.strftime('%H:%M') if order.slot_id else '—',
        'slot': order.slot.label if order.slot_id else '',
        'status': order.fulfillment_status,
        'method': order.get_method_display(),
        'where': _where(order),
        'total': rial_to_toman(order.grand_total_rial),
        'paid': rial_to_toman(order.paid_rial),
        'payMethod': _pay_method(order),
        'payStatus': order.get_payment_status_display(),
        # کیک اختصاصی تا وقتی مدیر قیمت نهایی نداده، جمعش برآورد است.
        'estimate': any(cake.quoted_price_rial is None for cake in cakes),
        'custom': bool(cakes),
        'since': _iso(user.created_at) if user else _iso(order.placed_at),
        'pastOrders': user.orders_count if user else 0,
        'warn': _warn(order),
        'gift': (('بسته‌بندی هدیه' + (f' — «{order.gift_message}»' if order.gift_message else ''))
                 if order.gift_wrap else ''),
        'staffNote': order.staff_note,
        'version': order.version,
        'items': items,
    }
    if order.fulfillment_status == FulfillmentStatus.CANCELED:
        data['cancel'] = {
            'reason': order.cancel_reason,
            'at': _iso(order.canceled_at),
            'by': order.canceled_by.get_short_name() if order.canceled_by_id else '',
        }
    if history:
        data['history'] = _history(order)
    return data
