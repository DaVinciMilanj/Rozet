"""
ویزارد کیک اختصاصی.

شش مرحله: شرایط، مشخصات، طرح، جزئیات، تأیید، و صفحه‌ی پایان. مراحل در
مرورگر اجرا می‌شوند؛ اینجا داده‌ی اولیه ساخته و درخواست ثبت می‌شود.

**ثبت نهایی فقط برای کاربر واردشده.** مشتری می‌تواند ویزارد را ببیند و
پر کند، ولی لحظه‌ی ثبت باید حساب داشته باشد. دلیلش کسب‌وکاری است نه
فنی: این سفارش بیعانه می‌گیرد، سرقناد بعداً قیمت قطعی را اعلام می‌کند و
مشتری باید بتواند وضعیتش را در پنل دنبال کند و در مهلت لغو کند. بدون
حساب هیچ‌کدام ممکن نیست.

**قیمت اینجا برآورد است، نه فاکتور.** قیمت قطعی را سرقناد پس از دیدن
طرح اعلام می‌کند. همان‌طور که هر جای دیگر پروژه، برآورد را هم سرور از
روی دیتابیس می‌سازد — نه از عددی که مرورگر فرستاده.
"""

import json
from datetime import timedelta

from django.conf import settings
from django.core.exceptions import ValidationError
from django.db import transaction
from django.http import JsonResponse
from django.templatetags.static import static
from django.urls import reverse
from django.utils import timezone
from django.views import View
from django.views.generic import TemplateView

from apps.catalog.models import Occasion
from apps.common import seo
from apps.common.dates import jalali_date
from apps.common.images import detect_upload
from apps.common.models import Pricing
from apps.payments import gateway
from apps.payments.models import PaymentKind
from apps.common.money import rial_to_toman
from apps.common.text import (fix_letters, normalize_phone, parse_int,
                              to_persian_digits)

from .convert import to_order
from .models import (CakeCoating, CakeFilling, CakeFlavor, CakeImageKind, CakeMode,
                     CakeSize, CakeTerm, CustomCakeImage, CustomCakeRequest)

# برآورد یک بازه است نه یک عدد: کار دست‌ساز و طرح‌های متفاوت، قیمت را
# جابه‌جا می‌کنند. همان ضریب‌هایی که تمپلیت نشان می‌داد.
ESTIMATE_LOW = 0.90
ESTIMATE_HIGH = 1.15

MAX_IMAGE_BYTES = 5 * 1024 * 1024


def _options(queryset):
    return [{'id': str(row.pk), 'label': row.label, 'sub': row.description,
             'add': rial_to_toman(row.price_delta_rial)}
            for row in queryset]


def _sizes():
    return [{'id': str(row.pk), 'label': row.label, 'sub': row.serves,
             'base': rial_to_toman(row.base_price_rial),
             'tiers': row.max_tiers}
            for row in CakeSize.objects.active()]


def wizard_seed(request):
    pricing = Pricing.load()
    user = request.user
    terms = list(CakeTerm.objects.active())
    earliest = timezone.localdate() + timedelta(days=settings.CUSTOM_CAKE_MIN_DAYS)

    return {
        # فهرست بندها و نسخه‌شان از دیتابیس می‌آید: وقتی مشتری شرایط را
        # می‌پذیرد، باید بدانیم **کدام نسخه** را پذیرفته.
        'terms': [{'title': t.title, 'text': t.text} for t in terms],
        'termsVersion': terms[0].version if terms else '',
        'sizes': _sizes(),
        'flavors': _options(CakeFlavor.objects.active()),
        'fillings': _options(CakeFilling.objects.active()),
        'coatings': _options(CakeCoating.objects.active()),
        'occasions': [{'id': str(o.pk), 'label': o.name}
                      for o in Occasion.objects.active()],
        'rules': {
            'minDays': settings.CUSTOM_CAKE_MIN_DAYS,
            'earliest': earliest.isoformat(),
            'earliestLabel': to_persian_digits(jalali_date(earliest)),
            'maxImages': settings.CUSTOM_CAKE_MAX_IMAGES,
            'maxBytes': MAX_IMAGE_BYTES,
            'cancelHours': settings.CUSTOM_CAKE_CANCEL_HOURS,
        },
        'fees': {
            'deposit': rial_to_toman(pricing.custom_deposit_rial),
            'print': rial_to_toman(pricing.custom_print_fee_rial),
        },
        # صفحه باید بداند کاربر وارد شده یا نه تا در مرحله‌ی تأیید
        # به‌جای دکمه‌ی ثبت، دعوت به ورود نشان دهد.
        'auth': {
            'in': user.is_authenticated,
            'url': f'{settings.LOGIN_URL}?next={reverse("custom_cake:wizard")}',
            'name': user.full_name if user.is_authenticated else '',
            'phone': user.phone if user.is_authenticated else '',
        },
        'urls': {'account': reverse('accounts:account')},
    }


class CustomCakeView(TemplateView):
    """ویزارد — /custom-cake/  (دیدنش برای همه آزاد است)"""

    template_name = 'custom_cake/wizard.html'

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['wizard_data'] = wizard_seed(self.request)
        context['seo'] = self._seo()
        return context

    def _seo(self):
        request = self.request
        city = settings.CAFE['city']
        url = reverse('custom_cake:wizard')
        return seo.build(
            request,
            title=f'سفارش کیک تولد و کیک اختصاصی با طرح دلخواه در {city} | {seo.SITE_NAME}',
            description=(f'کیک تولد و کیک مراسم را در {city} آنلاین طراحی کنید: طرح دلخواه '
                         'یا چاپ عکس خوراکی، اندازه و طعم انتخابی و برآورد قیمت آنی؛ '
                         f'دست‌کم {to_persian_digits(settings.CUSTOM_CAKE_MIN_DAYS)} روز پیش از مراسم.'),
            image=static('assets/images/custom-cake.webp'),
            image_alt='کیک اختصاصی رُزِت',
            jsonld=[
                seo.breadcrumbs(request, seo.home_trail() + [('کیک اختصاصی', url)]),
                {
                    '@context': seo.SCHEMA,
                    '@type': 'Service',
                    'name': 'سفارش کیک اختصاصی',
                    'serviceType': 'کیک تولد و کیک مراسم با طرح دلخواه',
                    'url': seo.absolute(request, url),
                    'provider': {'@id': f'{seo.site_url(request)}/#bakery'},
                    'areaServed': {'@type': 'City', 'name': city},
                },
            ])


class CustomCakeApiView(View):
    """POST multipart — ثبت درخواست. فقط برای کاربر واردشده."""

    def post(self, request):
        if not request.user.is_authenticated:
            # ۴۰۱ و نه ریدایرکت: fetch ریدایرکت را دنبال می‌کند و HTML
            # صفحه‌ی ورود را می‌گیرد، و کلاینت فکر می‌کند ثبت شده.
            return JsonResponse({
                'ok': False, 'auth': False,
                'error': 'برای ثبت سفارش کیک اختصاصی باید وارد حساب شوید.',
                'login': f'{settings.LOGIN_URL}?next={reverse("custom_cake:wizard")}',
            }, status=401)

        try:
            data = json.loads(request.POST.get('payload') or '{}')
        except json.JSONDecodeError:
            return self.fail('درخواست نامعتبر است.')
        if not isinstance(data, dict):
            return self.fail('درخواست نامعتبر است.')

        return self._submit(request, data)

    @staticmethod
    def fail(message, step=None, status=400):
        return JsonResponse({'ok': False, 'error': message, 'step': step}, status=status)

    def _submit(self, request, data):
        pricing = Pricing.load()

        if not data.get('terms'):
            return self.fail('برای ادامه باید شرایط سفارش را بپذیرید.', step=1)

        name = fix_letters(str(data.get('name', ''))).strip()
        family = fix_letters(str(data.get('family', ''))).strip()
        phone = normalize_phone(data.get('phone', ''))
        if len(name) < 2 or len(family) < 2:
            return self.fail('نام و نام خانوادگی را کامل بنویسید.', step=2)
        if len(phone) != 11 or not phone.startswith('09'):
            return self.fail('شماره باید با ۰۹ شروع شود و ۱۱ رقم باشد.', step=2)

        mode = (CakeMode.PRINT if data.get('mode') == CakeMode.PRINT
                else CakeMode.REFERENCE)

        event_date, error = self._event_date(data)
        if error:
            return self.fail(error, step=4)

        # همه‌ی شناسه‌ها از میان مقدارهای عددی رد می‌شوند: فرمِ ناقص
        # رشته‌ی خالی می‌فرستد و ``filter(pk='')`` خطای ۵۰۰ می‌دهد.
        def pick(model, key):
            pk = parse_int(data.get(key))
            return None if pk is None else model.objects.active().filter(pk=pk).first()

        # این چهار مورد اجباری‌اند. اگر گزینه‌ای بین بازکردن صفحه و ثبت
        # از دسترس خارج شود، پیام باید بگوید کدام — نه «این فیلد نمی‌تواند
        # پوچ باشد» که برای مشتری هیچ معنایی ندارد.
        chosen = {}
        for key, model, label in (('size', CakeSize, 'اندازه‌ی کیک'),
                                  ('flavor', CakeFlavor, 'طعم کیک'),
                                  ('filling', CakeFilling, 'فیلینگ'),
                                  ('coating', CakeCoating, 'طعم روکش')):
            chosen[key] = pick(model, key)
            if chosen[key] is None:
                return self.fail(f'{label} را انتخاب کنید.', step=4)

        size = chosen['size']
        flavor = chosen['flavor']
        filling = chosen['filling']
        coating = chosen['coating']
        occasion = pick(Occasion, 'occasion')

        files, error = self._images(request, mode)
        if error:
            return self.fail(error, step=3)

        # ── برآورد، از روی دیتابیس ──
        base = size.base_price_rial
        for option in (flavor, filling, coating):
            if option is not None:
                base += option.price_delta_rial
        print_fee = pricing.custom_print_fee_rial if mode == CakeMode.PRINT else 0
        base += print_fee

        tiers = max(1, min(parse_int(data.get('tiers'), 1), size.max_tiers))

        with transaction.atomic():
            cake = CustomCakeRequest(
                user=request.user,
                contact_name=name[:60], contact_family=family[:60],
                contact_phone=phone,
                contact_phone_alt=normalize_phone(data.get('phone2', '')),
                address=str(data.get('address', ''))[:500],
                mode=mode, size=size, flavor=flavor, filling=filling,
                coating=coating, occasion=occasion, tiers=tiers,
                color_theme=str(data.get('color', ''))[:80],
                message_on_cake=str(data.get('message', ''))[:60],
                design_note=str(data.get('note', ''))[:1000],
                allergy_note=str(data.get('allergy', ''))[:500],
                event_date=event_date,
                estimate_min_rial=int(base * ESTIMATE_LOW),
                estimate_max_rial=int(base * ESTIMATE_HIGH),
                deposit_rial=pricing.custom_deposit_rial,
                print_fee_rial=print_fee,
                terms_accepted_at=timezone.now(),
                terms_version=str(data.get('termsVersion', ''))[:20],
                cancel_deadline=timezone.now() + timedelta(
                    hours=settings.CUSTOM_CAKE_CANCEL_HOURS),
            )
            try:
                cake.full_clean(exclude=['code', 'order', 'reviewed_by'])
            except ValidationError as error:
                return self.fail(' '.join(sum(error.message_dict.values(), [])), step=4)
            cake.save()

            kind = (CakeImageKind.PRINT if mode == CakeMode.PRINT
                    else CakeImageKind.REFERENCE)
            for index, (upload, content_type) in enumerate(files):
                CustomCakeImage.objects.create(
                    request=cake, image=upload, kind=kind, sort_order=index,
                    content_type=content_type, size_bytes=upload.size)

        return JsonResponse({
            'ok': True,
            'code': to_persian_digits(cake.code),
            'date': to_persian_digits(jalali_date(cake.event_date)),
            'estimate': {
                'min': rial_to_toman(cake.estimate_min_rial),
                'max': rial_to_toman(cake.estimate_max_rial),
            },
            'deposit': rial_to_toman(cake.deposit_rial),
            'cancelUntil': to_persian_digits(
                jalali_date(timezone.localtime(cake.cancel_deadline))),
            **self._start_deposit(cake, request),
        })

    # ── اجزا ───────────────────────────────────────────────────────

    def _event_date(self, data):
        """
        تاریخ تحویل.

        زودتر از حداقل مهلت پذیرفته نمی‌شود — نه به این دلیل که فرم
        می‌گوید، بلکه چون آشپزخانه واقعاً نمی‌رسد.
        """
        raw = str(data.get('date', '')).strip()
        try:
            year, month, day = (int(part) for part in raw.split('-'))
            event_date = timezone.datetime(year, month, day).date()
        except (ValueError, TypeError):
            return None, 'تاریخ تحویل را انتخاب کنید.'

        earliest = timezone.localdate() + timedelta(days=settings.CUSTOM_CAKE_MIN_DAYS)
        if event_date < earliest:
            return None, (f'زودترین تاریخ ممکن '
                          f'{to_persian_digits(jalali_date(earliest))} است.')
        if event_date > timezone.localdate() + timedelta(days=365):
            return None, 'تاریخ تحویل بیش از حد دور است.'
        return event_date, None

    def _images(self, request, mode):
        files = request.FILES.getlist('images')[:settings.CUSTOM_CAKE_MAX_IMAGES]
        if mode == CakeMode.PRINT and not files:
            return None, 'برای چاپ عکس خوراکی، دست‌کم یک تصویر لازم است.'
        checked = []
        for upload in files:
            if upload.size > MAX_IMAGE_BYTES:
                return None, f'حجم «{upload.name}» بیش از حد مجاز است.'
            # نوع از روی محتوا، نه پسوند: این فایل‌ها بعداً برای کارکنان
            # باز می‌شوند و یک SVGِ اسکریپت‌دار با نشست آن‌ها اجرا می‌شد.
            content_type = detect_upload(upload)
            if content_type is None:
                return None, (f'«{upload.name}» تصویر معتبری نیست؛ '
                              'فقط JPG، PNG، WebP یا HEIC آیفون.')
            checked.append((upload, content_type))
        return checked, None

    def _start_deposit(self, cake, request):
        """
        بیعانه را از راه لایه‌ی درگاه می‌گیرد.

        اینجا هیچ چیزی درباره‌ی زرین‌پال نمی‌داند و نباید بداند: فقط
        ``gateway.start`` را صدا می‌زند. اگر درگاه نشانی‌ای برگرداند،
        همان به کلاینت می‌رود و کاربر به بانک می‌رود؛ اگر نه، پرداخت
        همان‌جا تمام شده است.

        امروز درگاهِ آزمایشی پاسخ می‌دهد و بیعانه بی‌درنگ «موفق» ثبت
        می‌شود. برای وصل‌کردن درگاه واقعی، فقط
        ``settings.PAYMENT_GATEWAY`` عوض می‌شود.
        """
        if cake.deposit_rial <= 0:
            to_order(cake)
            return {'payment': 'none'}

        payment, redirect = gateway.start(
            amount_rial=cake.deposit_rial, kind=PaymentKind.DEPOSIT,
            custom_cake=cake, request=request)

        if redirect:
            # سفارش آشپزخانه بعد از تأیید درگاه ساخته می‌شود — در بازگشت
            # از بانک، با همان ``to_order``.
            return {'payment': 'redirect', 'redirect': redirect}

        if payment.is_successful:
            # بیعانه رسید؛ کیک همین حالا روی تابلوی آشپزخانه می‌آید.
            to_order(cake)

        return {
            'payment': 'paid' if payment.is_successful else 'pending',
            'sandbox': payment.is_sandbox,
            'refId': payment.ref_id,
            'note': ('بیعانه پرداخت شد و درخواست شما ثبت است.'
                     if payment.is_successful else
                     'برای هماهنگی بیعانه با شما تماس می‌گیریم.'),
        }
