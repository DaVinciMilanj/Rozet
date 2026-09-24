"""
ثبت سفارش.

صفحه پنج مرحله دارد (نحوه‌ی دریافت، زمان، مشخصات، جزئیات، پرداخت) و
همه‌ی آن‌ها در مرورگر اجرا می‌شوند. اینجا فقط دو کار انجام می‌شود:
داده‌ی اولیه‌ی صفحه ساخته می‌شود، و سفارش ثبت می‌شود.

**قاعده‌ی مرکزی: هیچ عددی از مرورگر پذیرفته نمی‌شود.** مرورگر جمع‌ها را
برای نمایش حساب می‌کند، ولی هنگام ثبت، سرور همه‌چیز را از نو می‌سازد —
قیمت اقلام از دیتابیس، هزینه‌ی ارسال از ``Pricing``، تخفیف از
``PromoCode``. اگر عدد سمت مرورگر دست‌کاری شده باشد، هیچ اثری ندارد.

**درگاه پرداخت هنوز وصل نیست.** سفارش ثبت می‌شود و «پرداخت‌نشده» می‌ماند؛
جای دقیق اتصال درگاه در ``_start_payment`` علامت خورده است.
"""

import json
from datetime import timedelta

from django.conf import settings
from django.db import transaction
from django.http import JsonResponse
from django.urls import reverse
from django.utils import timezone
from django.views import View
from django.views.generic import TemplateView

from apps.common.dates import jalali_long
from apps.common.models import Pricing
from apps.payments import gateway
from apps.payments.models import PaymentKind
from apps.common.money import rial_to_toman
from apps.common.text import (fix_letters, normalize_phone, parse_int,
                              to_persian_digits)

from .cart import cart_payload, get_cart
from .models import (DeliveryMethod, DeliverySlot, Order, OrderItem, OrderItemKind,
                     PayMethod, PaymentStatus, PromoCode)


def _slots():
    return [{'id': str(slot.pk), 'from': slot.start_time.hour, 'label': slot.label}
            for slot in DeliverySlot.objects.filter(is_active=True)
            .order_by('sort_order', 'start_time')]


def _days():
    """
    روزهای قابل انتخاب.

    تاریخ شمسی را سرور می‌سازد نه مرورگر: تمپلیت از
    ``toLocaleDateString('fa-IR')`` استفاده می‌کرد که روی هر مرورگر و
    هر سیستم‌عاملی می‌تواند فرق کند، و تاریخی که مشتری می‌بیند باید
    همانی باشد که روی برگه‌ی آشپزخانه می‌نشیند.
    """
    today = timezone.localdate()
    out = []
    for offset in range(settings.CHECKOUT_CALENDAR_DAYS):
        day = today + timedelta(days=offset)
        long_form = jalali_long(day)          # «پنجشنبه ۱۴۰۴/۰۶/۱۲»
        weekday, _, date_part = long_form.partition(' ')
        out.append({
            'i': offset,
            'iso': day.isoformat(),
            'top': 'امروز' if offset == 0 else ('فردا' if offset == 1 else weekday),
            'num': date_part,
            'full': long_form,
        })
    return out


def _profile(request):
    user = request.user
    if not user.is_authenticated:
        return {'name': '', 'phone': '', 'addresses': []}
    return {
        'name': user.full_name,
        'phone': user.phone,
        'addresses': [{'id': a.pk, 't': a.title, 'x': a.one_line, 'def': a.is_default}
                      for a in user.addresses.alive()],
    }


def checkout_seed(request):
    cart = get_cart(request, create=False)
    pricing = Pricing.load()
    return {
        'items': cart_payload(cart),
        'slots': _slots(),
        'days': _days(),
        'profile': _profile(request),
        # نرخ‌ها از مدل Pricing می‌آیند نه از ثابت‌های داخل جاوااسکریپت:
        # این‌ها با تورم عوض می‌شوند و مدیر باید بتواند از پنل تغییرشان
        # دهد، نه اینکه هر بار کد دست بخورد.
        'fees': {
            'courier': pricing.courier_enabled,
            'ship': rial_to_toman(pricing.delivery_fee_rial),
            'freeOver': rial_to_toman(pricing.free_delivery_over_rial),
            'gift': rial_to_toman(pricing.gift_wrap_rial),
            'vat': float(pricing.vat_percent) if pricing.vat_enabled else 0,
        },
        'urls': {
            'products': reverse('catalog:product_list'),
            'account': reverse('accounts:account'),
        },
    }


class CheckoutView(TemplateView):
    template_name = 'orders/checkout.html'

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['checkout_data'] = checkout_seed(self.request)
        return context


class CheckoutApiView(View):
    """POST {action: 'promo'|'place', ...}"""

    def post(self, request):
        try:
            data = json.loads(request.body or '{}')
        except (json.JSONDecodeError, UnicodeDecodeError):
            return self.fail('درخواست نامعتبر است.')
        if not isinstance(data, dict) or data.get('action') not in {'promo', 'place'}:
            return self.fail('درخواست نامعتبر است.')
        return getattr(self, '_' + data['action'])(request, data)

    @staticmethod
    def fail(message, status=400, **extra):
        return JsonResponse({'ok': False, 'error': message, **extra}, status=status)

    # ── کد تخفیف ───────────────────────────────────────────────────

    def _promo(self, request, data):
        """
        اعتبارسنجی کد — بدون ثبت مصرف.

        مصرف هنگام ثبت سفارش شمرده می‌شود، وگرنه هر بار که کسی کدی را
        در کادر تایپ می‌کرد، سهمیه‌اش می‌سوخت.
        """
        cart = get_cart(request, create=False)
        items_total = cart.items_total_rial if cart else 0
        if not items_total:
            return self.fail('سبد خرید خالی است.')

        code = str(data.get('code', '')).strip()
        promo = PromoCode.objects.filter(code__iexact=code).first()
        if promo is None or not promo.is_running:
            return self.fail('این کد معتبر نیست.')
        if items_total < promo.min_order_rial:
            return self.fail(
                f'این کد برای سفارش بالای {to_persian_digits(rial_to_toman(promo.min_order_rial))} تومان است.')

        discount = promo.discount_for(items_total)
        if not discount:
            return self.fail('این کد برای این سبد تخفیفی ندارد.')

        return JsonResponse({
            'ok': True,
            'code': promo.code,
            'label': promo.description or promo.code,
            'off': rial_to_toman(discount),
        })

    # ── ثبت سفارش ──────────────────────────────────────────────────

    def _place(self, request, data):
        cart = get_cart(request, create=False)
        rows = list(cart.items.select_related('product', 'size', 'flavor')
                    .prefetch_related('addons')) if cart else []
        if not rows:
            return self.fail('سبد خرید خالی است.')

        name = fix_letters(str(data.get('name', ''))).strip()
        phone = normalize_phone(data.get('phone', ''))
        if len(name) < 3:
            return self.fail('نام و نام خانوادگی را کامل بنویسید.', field='who')
        if len(phone) != 11 or not phone.startswith('09'):
            return self.fail('شماره باید با ۰۹ شروع شود و ۱۱ رقم باشد.', field='who')
        if not data.get('terms'):
            return self.fail('برای ثبت سفارش باید شرایط را بپذیرید.', field='pay')

        pricing = Pricing.load()
        method = (DeliveryMethod.COURIER
                  if data.get('method') == DeliveryMethod.COURIER and pricing.courier_enabled
                  else DeliveryMethod.PICKUP)

        due_date, slot = self._when(data)
        if due_date is None:
            return self.fail('روز و بازه‌ی ساعت را انتخاب کنید.', field='when')

        snapshot, error = self._address(request, data, method)
        if error:
            return self.fail(error, field='who')

        # ── جمع‌ها، همه از دیتابیس ──
        items_total = sum(row.line_total_rial for row in rows)
        gift = bool(data.get('gift'))
        gift_fee = pricing.gift_wrap_rial if gift else 0
        delivery_fee = (pricing.delivery_fee_for(items_total)
                        if method == DeliveryMethod.COURIER else 0)

        promo, discount = self._promo_for(request, data, items_total)
        taxable = max(0, items_total - discount) + gift_fee + delivery_fee
        vat = pricing.vat_for(taxable)
        grand_total = taxable + vat

        pay_method = (PayMethod.ONLINE if data.get('pay') == PayMethod.ONLINE
                      else PayMethod.ONSITE)

        with transaction.atomic():
            order = Order(
                user=request.user if request.user.is_authenticated else None,
                customer_name=name[:120], customer_phone=phone,
                method=method, due_date=due_date, slot=slot,
                pay_method=pay_method, payment_status=PaymentStatus.UNPAID,
                items_total_rial=items_total,
                discount_rial=discount,
                delivery_fee_rial=delivery_fee,
                gift_wrap_rial=gift_fee,
                vat_rial=vat,
                vat_percent=pricing.vat_percent,
                grand_total_rial=grand_total,
                promo=promo,
                gift_wrap=gift,
                gift_message=str(data.get('plaque', ''))[:60],
                allergy_note=str(data.get('allergy', ''))[:300],
                customer_note=str(data.get('note', ''))[:500],
                address_snapshot=snapshot,
            )
            order.save()

            for row in rows:
                bits = [x for x in (row.size.label if row.size_id else '',
                                    row.flavor.label if row.flavor_id else '') if x]
                bits += [addon.label for addon in row.addons.all()]
                cover = row.product.cover
                OrderItem.objects.create(
                    order=order, kind=OrderItemKind.CATALOGUE, product=row.product,
                    name=row.product.name[:140],
                    size_label=row.size.label[:80] if row.size_id else '',
                    flavor_label=' · '.join(bits[1:])[:80] if len(bits) > 1 else '',
                    # اسنپ‌شات تصویر: نامِ فایل کپی می‌شود نه خودِ فایل، و
                    # سیگنال پاک‌سازی حواسش هست که فایل مشترک را نبرد.
                    image=cover.image.name if cover else '',
                    message_on_cake=row.message_on_cake[:60],
                    quantity=row.quantity,
                    unit_price_rial=row.unit_price_rial,
                    line_total_rial=row.line_total_rial)

            if promo is not None:
                PromoCode.objects.filter(pk=promo.pk).update(
                    used_count=promo.used_count + 1)

            cart.items.all().delete()

        return JsonResponse({
            'ok': True,
            'code': to_persian_digits(order.code),
            'when': to_persian_digits(
                jalali_long(order.due_date) + (f' — ساعت {slot.label}' if slot else '')),
            'total': rial_to_toman(order.grand_total_rial),
            **self._start_payment(order, request),
        })

    # ── اجزا ───────────────────────────────────────────────────────

    def _when(self, data):
        """روز و بازه — هر دو باید از فهرستی باشند که خودِ سرور داده."""
        offset = parse_int(data.get('day'))
        if offset is None or not 0 <= offset < settings.CHECKOUT_CALENDAR_DAYS:
            return None, None

        slot_id = parse_int(data.get('slot'))
        slot = (DeliverySlot.objects.filter(pk=slot_id, is_active=True).first()
                if slot_id is not None else None)
        if slot is None:
            return None, None
        return timezone.localdate() + timedelta(days=offset), slot

    def _address(self, request, data, method):
        """
        اسنپ‌شات نشانی.

        ارجاع به رکورد نشانی کافی نیست: اگر مشتری فردا نشانی را ویرایش
        کند، برگه‌ی سفارشِ دیروز نباید عوض شود.
        """
        if method != DeliveryMethod.COURIER:
            return {}, None

        raw = str(data.get('addr', '')).strip()
        address_id = parse_int(data.get('addrId'))
        if address_id is not None and request.user.is_authenticated:
            saved = request.user.addresses.alive().filter(pk=address_id).first()
            if saved is not None:
                return saved.to_snapshot(), None

        if len(raw) < 10:
            return None, 'نشانی تحویل را کامل بنویسید.'
        return {'line': raw[:300], 'city': settings.CAFE['city']}, None

    def _promo_for(self, request, data, items_total):
        code = str(data.get('promo') or '').strip()
        if not code:
            return None, 0
        promo = PromoCode.objects.filter(code__iexact=code).first()
        if promo is None or not promo.is_running or items_total < promo.min_order_rial:
            # کد بی‌اعتبار سفارش را زمین نمی‌زند؛ فقط تخفیفی نمی‌دهد.
            return None, 0
        return promo, promo.discount_for(items_total)

    def _start_payment(self, order, request):
        """
        پرداخت را از راه لایه‌ی درگاه شروع می‌کند.

        این تابع هیچ چیزی درباره‌ی زرین‌پال نمی‌داند: فقط
        ``gateway.start`` را صدا می‌زند و اگر نشانی‌ای برگشت، به کلاینت
        می‌دهد. برای وصل‌کردن درگاه واقعی، ``settings.PAYMENT_GATEWAY``
        عوض می‌شود و همین‌جا دست نمی‌خورد.

        «پرداخت در محل» اصلاً از درگاه رد نمی‌شود؛ پولش را کارمند کافه
        هنگام تحویل می‌گیرد و در پنل ثبت می‌کند.
        """
        if order.pay_method != PayMethod.ONLINE:
            return {'payment': 'onsite'}

        payment, redirect = gateway.start(
            amount_rial=order.grand_total_rial, kind=PaymentKind.FULL,
            order=order, request=request)

        if redirect:
            return {'payment': 'redirect', 'redirect': redirect}

        if payment.is_successful:
            # سفارش را هم به‌روز می‌کنیم؛ دو ستونِ پول نباید از هم جدا
            # بیفتند.
            Order.objects.filter(pk=order.pk).update(
                paid_rial=order.grand_total_rial,
                payment_status=PaymentStatus.PAID)
            return {'payment': 'paid', 'sandbox': payment.is_sandbox,
                    'refId': payment.ref_id,
                    'note': 'پرداخت با موفقیت انجام شد.'}

        return {'payment': 'pending',
                'note': 'پرداخت تأیید نشد؛ همکاران ما با شما هماهنگ می‌کنند.'}
