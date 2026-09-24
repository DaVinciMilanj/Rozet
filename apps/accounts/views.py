"""
پنل حساب کاربری.

صفحه در تمپلیت یک اپ کامل سمت کلاینت است: پنج نما، مودال آدرس، فیلتر و
جست‌وجوی سفارش، حلقه‌ی باشگاه. همان قاعده‌ی صفحه‌های قبلی اینجا هم برقرار
است — مارکاپ و منطق دست نمی‌خورد، فقط **منبع داده** عوض می‌شود.

دو درز برای همین در فایل جاوااسکریپت بود و هر دو وصل می‌شوند:

* ``SEED`` — آرایه‌ی ثابت بالای فایل، که جایش را به ``json_script`` می‌دهد.
* ``api(action, payload)`` — تابعی که فقط وانمود می‌کرد ذخیره می‌کند.

به همین دلیل نوشتن‌ها **یک** اندپوینت دارند که روی ``action`` تقسیم
می‌کند، نه هشت آدرس جدا: امضای سمت کلاینت همان می‌ماند.
"""

import json

from django.conf import settings
from django.contrib.auth import logout, update_session_auth_hash
from django.contrib.auth.decorators import login_required
from django.contrib.auth.password_validation import validate_password
from django.core.exceptions import ValidationError
from django.db import transaction
from django.http import JsonResponse
from django.templatetags.static import static
from django.urls import reverse
from django.utils import timezone
from django.utils.decorators import method_decorator
from django.views import View
from django.views.generic import TemplateView

from apps.common.dates import jalali_date, jalali_long
from apps.common.money import format_toman, rial_to_toman
from apps.common.text import fix_digits, normalize_phone, to_persian_digits
from apps.orders.models import DeliveryMethod, FulfillmentStatus, Order, PaymentStatus

from .models import Address

# تصویری که وقتی محصولی عکس ندارد نشان داده می‌شود. رشته‌ی خالی نمی‌شود:
# ``src=""`` مرورگر را وادار می‌کند خودِ صفحه را دوباره بگیرد.
PLACEHOLDER = 'assets/images/brand-story.webp'

# تمپلیت وضعیت «تازه» را ``placed`` می‌نامد و دیتابیس ``new``. نگاشت
# همین‌جا انجام می‌شود تا ``STATUS`` در جاوااسکریپت دست‌نخورده بماند.
STATUS_MAP = {FulfillmentStatus.NEW: 'placed'}

CAFE = settings.CAFE
PICKUP_ADDRESS = f"{CAFE['city']}، {CAFE['address']} — شعبه‌ی {CAFE['name']}"


def _image(file):
    return file.url if file else static(PLACEHOLDER)


def _profile(user):
    return {
        'first': user.first_name,
        'last': user.last_name,
        'phone': user.phone,
        'email': user.email,
        # رشته، نه عدد: مقدارِ <option> با رشته مقایسه می‌شود و صفر یا
        # None باعث می‌شود سلکت روی گزینه‌ی خالی نایستد.
        'bDay': str(user.birth_day or ''),
        'bMonth': str(user.birth_month or ''),
        'bYear': str(user.birth_year or ''),
        'sms': user.sms_opt_in,
        'news': user.email_opt_in,
    }


def _address(address):
    """شکلی که account.js می‌شناسد: t عنوان، x نشانی، r گیرنده، c شماره."""
    return {
        'id': address.pk,
        't': address.title,
        'x': address.one_line,
        'r': address.receiver_name,
        'c': address.receiver_phone,
        'def': address.is_default,
    }


def _payment_line(order):
    """
    یک جمله درباره‌ی پرداخت — «پرداخت کامل — پرداخت آنلاین».

    در تمپلیت این یک رشته‌ی آماده بود؛ اینجا از دو ستونِ وضعیت و مبلغ
    ساخته می‌شود تا «بیعانه» عددش را هم بگوید.
    """
    if order.payment_status == PaymentStatus.PAID:
        return f'پرداخت کامل — {order.get_pay_method_display()}'
    if order.payment_status == PaymentStatus.DEPOSIT:
        return f'پیش‌پرداخت {format_toman(order.paid_rial)} تومان'
    if order.payment_status == PaymentStatus.REFUNDED:
        return 'پیش‌پرداخت بازگردانده شد'
    return 'پرداخت نشده'


def _order(order):
    data = {
        'code': order.code,
        'date': jalali_date(timezone.localtime(order.placed_at)),
        'status': STATUS_MAP.get(order.fulfillment_status, order.fulfillment_status),
        'method': order.get_method_display(),
        # نشانی حضوری از تنظیمات می‌آید، نه از رشته‌ی داخل کد: اگر
        # کافه جابه‌جا شود، یک جا عوض می‌شود نه چند جا.
        'addr': ((order.address_snapshot or {}).get('line', '')
                 if order.method == DeliveryMethod.COURIER
                 else PICKUP_ADDRESS),
        'pay': _payment_line(order),
        # مبلغ نهایی، نه جمع اقلام: ارسال و بسته‌ی هدیه و تخفیف در آن
        # حساب شده‌اند و تمپلیت همین را ملاک «جمع کل» می‌گیرد.
        'paid': rial_to_toman(order.grand_total_rial),
        'note': order.cancel_reason,
        'items': [{
            'n': item.name,
            's': ' · '.join(x for x in (item.size_label, item.flavor_label) if x),
            'q': item.quantity,
            'p': rial_to_toman(item.unit_price_rial),
            'i': _image(item.image),
        } for item in order.items.all()],
    }
    if order.is_open:
        slot = f' — ساعت {order.slot.label}' if order.slot_id else ''
        data['ready'] = to_persian_digits(jalali_long(order.due_date) + slot)
    return data


def _stats(user, orders):
    """
    سه عدد بالای صفحه و پله‌ی باشگاه — از خودِ حساب، نه از روی آرایه‌ی
    نمایش.

    ``orders`` و ``spent`` همه‌ی سفارش‌های لغونشده را می‌شمارند، پس با
    فهرستی که کاربر جلوی چشمش دارد جور درمی‌آیند. ``club`` اما شمارنده‌ی
    خودِ مدل است (``orders_count``) که فقط با «تحویل شد» بالا می‌رود —
    باشگاه به سفارش تحویل‌شده جایزه می‌دهد، نه به سفارش ثبت‌شده.
    """
    live = [order for order in orders
            if order.fulfillment_status != FulfillmentStatus.CANCELED]
    return {
        'orders': len(live),
        'spent': rial_to_toman(sum(order.grand_total_rial for order in live)),
        'club': user.orders_count,
    }


def account_seed(user):
    """داده‌ی همین کاربر — چیزی بیرون از رکورد خودش در این payload نیست."""
    orders = (Order.objects.filter(user=user)
              .select_related('slot')
              .prefetch_related('items')
              .order_by('-placed_at'))
    favorites = (user.favorites
                 .select_related('product')
                 .prefetch_related('product__images'))
    orders = list(orders)
    return {
        'profile': _profile(user),
        'stats': _stats(user, orders),
        # پله‌های باشگاه از LOYALTY_TIERS می‌آیند نه از جاوااسکریپت: دو
        # جای جدا یعنی روزی که مدیر پله‌ها را عوض کند، سرور یک چیز حساب
        # می‌کند و صفحه چیز دیگری نشان می‌دهد.
        'tiers': [list(row) for row in settings.LOYALTY_TIERS],
        # بدون سقف: فیلتر و جست‌وجوی سفارش‌ها در مرورگر انجام می‌شود، پس
        # هر سفارشی که بریده شود اصلاً قابل پیداکردن نیست.
        'orders': [_order(order) for order in orders],
        'favorites': [{
            'id': favorite.product_id,
            'n': favorite.product.name,
            'p': rial_to_toman(favorite.product.price_rial),
            'i': _image(favorite.product.cover.image if favorite.product.cover else None),
            'url': favorite.product.get_absolute_url(),
        } for favorite in favorites],
        'addresses': [_address(address) for address in user.addresses.alive()],
    }


@method_decorator(login_required, name='dispatch')
class AccountView(TemplateView):
    template_name = 'accounts/account.html'

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['account_data'] = account_seed(self.request.user)
        return context


@method_decorator(login_required, name='dispatch')
class AccountApiView(View):
    """
    همه‌ی نوشتن‌های پنل — یک آدرس، تقسیم روی ``action``.

    فقط POST، فقط برای کاربر واردشده، و هر رکوردی که دست می‌خورد اول
    بررسی می‌شود که مال خودِ اوست: بدون آن، عوض‌کردن یک عدد در درخواست
    یعنی حذف نشانی کس دیگری.
    """

    ACTIONS = {
        'profile-save', 'notify-save', 'password-change',
        'address-save', 'address-default', 'address-delete',
        'favorite-remove', 'account-delete',
    }

    def post(self, request):
        try:
            data = json.loads(request.body or '{}')
        except (json.JSONDecodeError, UnicodeDecodeError):
            return self.fail('درخواست نامعتبر است.')
        if not isinstance(data, dict):
            return self.fail('درخواست نامعتبر است.')

        action = data.get('action')
        # فهرست سفید، نه getattr روی هر رشته‌ای که برسد.
        if action not in self.ACTIONS:
            return self.fail('اکشن ناشناخته.')
        return getattr(self, '_' + action.replace('-', '_'))(request, data)

    @staticmethod
    def fail(message, status=400):
        return JsonResponse({'ok': False, 'error': message}, status=status)

    @staticmethod
    def text(data, key, limit):
        return str(data.get(key, '') or '').strip()[:limit]

    # ── پروفایل ────────────────────────────────────────────────────

    def _profile_save(self, request, data):
        user = request.user
        user.first_name = self.text(data, 'first', 60)
        user.last_name = self.text(data, 'last', 60)
        user.email = self.text(data, 'email', 254)

        # تاریخ تولد از سه سلکت می‌آید و می‌تواند خالی باشد. رقم فارسی
        # هم ممکن است: کاربر با کیبورد فارسی تایپ نمی‌کند ولی صفحه
        # عددها را فارسی نشان می‌دهد و کپی‌پیست همان را می‌فرستد.
        for field, key in (('birth_day', 'bDay'), ('birth_month', 'bMonth'),
                           ('birth_year', 'bYear')):
            raw = fix_digits(str(data.get(key, '') or '')).strip()
            setattr(user, field, int(raw) if raw.isdigit() else None)

        try:
            user.full_clean(exclude=['password', 'last_login'])
        except ValidationError as error:
            return self.fail(' '.join(sum(error.message_dict.values(), [])))

        user.save()
        return JsonResponse({'ok': True, 'profile': _profile(user)})

    def _notify_save(self, request, data):
        user = request.user
        user.sms_opt_in = bool(data.get('sms'))
        user.email_opt_in = bool(data.get('news'))
        user.save(update_fields=['sms_opt_in', 'email_opt_in', 'updated_at'])
        return JsonResponse({'ok': True})

    def _password_change(self, request, data):
        user = request.user
        # حسابی که با کد پیامکی ساخته شده رمز ندارد؛ آنجا «رمز فعلی»
        # چیزی نیست که بشود پرسید.
        if user.has_usable_password() and not user.check_password(data.get('old') or ''):
            return self.fail('رمز فعلی درست نیست.')

        new = data.get('next') or ''
        try:
            validate_password(new, user)
        except ValidationError as error:
            return self.fail(' '.join(error.messages))

        user.set_password(new)
        user.save(update_fields=['password'])
        # بدون این، کاربر با عوض‌کردن رمز از حساب خودش بیرون می‌افتد:
        # هش رمز در نشست ذخیره است و دیگر نمی‌خواند.
        update_session_auth_hash(request, user)
        return JsonResponse({'ok': True})

    # ── نشانی ──────────────────────────────────────────────────────

    def _own_address(self, request, data):
        try:
            return request.user.addresses.alive().get(pk=int(data.get('id')))
        except (Address.DoesNotExist, TypeError, ValueError):
            return None

    def _make_default(self, request, address):
        # قید یکتای جزئی روی دیتابیس هست، پس اول بقیه خاموش می‌شوند —
        # وگرنه ذخیره با IntegrityError برمی‌گردد.
        request.user.addresses.alive().exclude(pk=address.pk).update(is_default=False)
        if not address.is_default:
            address.is_default = True
            address.save(update_fields=['is_default', 'updated_at'])

    def _ensure_one_default(self, request):
        """اگر پیش‌فرض حذف شد، اولی جایش را می‌گیرد — مثل خود تمپلیت."""
        alive = request.user.addresses.alive()
        if alive.exists() and not alive.filter(is_default=True).exists():
            self._make_default(request, alive.first())

    @transaction.atomic
    def _address_save(self, request, data):
        address = None
        if data.get('id'):
            # شناسه‌ای که پیدا نشد یعنی مال کس دیگری است یا حذف شده. اینجا
            # نباید به ساختِ رکورد تازه بیفتیم: کاربر «ویرایش» زده و در
            # عمل یک نشانی بی‌صاحب اضافه می‌شد.
            address = self._own_address(request, data)
            if address is None:
                return self.fail('نشانی پیدا نشد.', status=404)
        else:
            if request.user.addresses.alive().count() >= 20:
                return self.fail('بیش از ۲۰ نشانی نمی‌شود ذخیره کرد.')
            address = Address(user=request.user)

        address.title = self.text(data, 't', 40)
        address.line = self.text(data, 'x', 300)
        address.receiver_name = self.text(data, 'r', 80) or request.user.full_name
        # نرمال‌سازی پیش از اعتبارسنجی، نه در save: وگرنه «۰۹۱۵…» با رقم
        # فارسی سرِ validate_phone رد می‌شود، پیش از آنکه اصلاح شود.
        address.receiver_phone = (normalize_phone(self.text(data, 'c', 20))
                                  or request.user.phone)

        try:
            address.full_clean(exclude=['user', 'deleted_at'])
        except ValidationError as error:
            return self.fail(' '.join(sum(error.message_dict.values(), [])))

        # همیشه خاموش ذخیره می‌شود و بعد در صورت نیاز روشن: قید یکتای
        # «یک پیش‌فرض برای هر کاربر» روی دیتابیس است و ذخیره‌ی مستقیمِ
        # پیش‌فرضِ دوم با IntegrityError برمی‌گردد.
        address.is_default = False
        address.save()
        if data.get('def'):
            self._make_default(request, address)
        else:
            # وقتی خودمان همین حالا یکی را پیش‌فرض کرده‌ایم، جست‌وجو برای
            # «آیا پیش‌فرضی هست؟» دو کوئری بی‌جهت است.
            self._ensure_one_default(request)

        address.refresh_from_db()
        return JsonResponse({'ok': True, 'address': _address(address)})

    @transaction.atomic
    def _address_default(self, request, data):
        address = self._own_address(request, data)
        if address is None:
            return self.fail('نشانی پیدا نشد.', status=404)
        self._make_default(request, address)
        return JsonResponse({'ok': True})

    @transaction.atomic
    def _address_delete(self, request, data):
        address = self._own_address(request, data)
        if address is None:
            return self.fail('نشانی پیدا نشد.', status=404)
        # حذف نرم: نشانی‌ای که مشتری اشتباهی پاک می‌کند باید قابل
        # بازگرداندن باشد. خودِ سفارش نسخه‌ی اسنپ‌شات دارد.
        address.delete()
        self._ensure_one_default(request)
        return JsonResponse({'ok': True})

    # ── علاقه‌مندی ─────────────────────────────────────────────────

    def _favorite_remove(self, request, data):
        try:
            product_id = int(data.get('id'))
        except (TypeError, ValueError):
            return self.fail('شناسه‌ی نامعتبر.')
        removed, _ = request.user.favorites.filter(product_id=product_id).delete()
        return JsonResponse({'ok': bool(removed)})

    # ── حذف حساب ───────────────────────────────────────────────────

    def _account_delete(self, request, data):
        """
        ناشناس‌سازی، نه DELETE.

        سفارش‌ها سند مالی‌اند و باید بمانند؛ فقط هویت پاک می‌شود. سفارش
        باز مانع است — وگرنه کیکی در فر می‌ماند که صاحبش دیگر قابل تماس
        نیست.
        """
        user = request.user
        if user.has_open_orders():
            return self.fail('سفارش در جریان دارید؛ پس از تحویل دوباره تلاش کنید.')

        user.anonymize()

        logout(request)
        return JsonResponse({'ok': True, 'redirect': reverse('pages:home')})
