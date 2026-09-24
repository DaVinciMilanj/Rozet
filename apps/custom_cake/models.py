"""
کیک اختصاصی — پیچیده‌ترین فرم تمپلیت.

منبع در تمپلیت:
    custom-cake/custom-cake.js   TERMS · SIZES · FLAVORS · FILLINGS · TEXTURES
                                 DEPOSIT · MIN_DAYS · PRINT_FEE · state
    admin/order-details.js       refs · refNote · print · printNote
"""

import random
import string

from django.conf import settings
from django.core.exceptions import ValidationError
from django.core.files.storage import storages
from django.core.validators import MinValueValidator
from django.db import models
from django.utils import timezone

from apps.common.fields import ImageField
from apps.common.models import (ActivatableModel, Pricing, SortableModel,
                                TimeStampedModel, save_with_unique_code)
from apps.common.text import normalize_phone
from apps.common.validators import validate_image_size, validate_phone
from apps.common import upload


def private_storage():
    """
    فضای ذخیره‌ی خصوصی.

    تابع است نه نمونه، تا مهاجرت بتواند با ارجاع سریالش کند و تغییر مسیر
    در تنظیمات، مهاجرت جدید نسازد.
    """
    return storages['private']


# ═══════════════════════════════════════════════════════════════════
#  گزینه‌های ویزارد
# ═══════════════════════════════════════════════════════════════════

class CakeOption(SortableModel, ActivatableModel):
    """پایه‌ی مشترک چهار جدول گزینه."""

    label = models.CharField('عنوان', max_length=60)
    description = models.CharField('توضیح', max_length=120, blank=True)
    price_delta_rial = models.BigIntegerField('اختلاف قیمت (ریال)', default=0)

    class Meta:
        abstract = True
        ordering = ('sort_order', 'id')

    def __str__(self):
        return self.label


class CakeSize(CakeOption):
    """
    اندازه — ``SIZES`` در custom-cake.js (هفت پله از ۴ نفر تا ۵۰ نفر).

    برخلاف سه جدول دیگر، اندازه **قیمت پایه** دارد نه اختلاف قیمت؛ کل
    برآورد از همین شروع می‌شود.
    """

    base_price_rial = models.BigIntegerField(
        'قیمت پایه (ریال)', validators=[MinValueValidator(0)])
    serves = models.CharField('تعداد نفرات', max_length=60, help_text='۱۲ تا ۱۵ نفر')
    approx_weight = models.CharField('وزن تقریبی', max_length=40, blank=True,
                                     help_text='حدود ۴ کیلو')
    max_tiers = models.SmallIntegerField('حداکثر طبقه', default=1)

    class Meta(CakeOption.Meta):
        verbose_name = 'اندازه کیک اختصاصی'
        verbose_name_plural = 'اندازه‌های کیک اختصاصی'


class CakeFlavor(CakeOption):
    """طعم پایه‌ی کیک — ``FLAVORS``."""

    class Meta(CakeOption.Meta):
        verbose_name = 'طعم کیک اختصاصی'
        verbose_name_plural = 'طعم‌های کیک اختصاصی'


class CakeFilling(CakeOption):
    """فیلینگ میان لایه‌ها — ``FILLINGS``."""

    class Meta(CakeOption.Meta):
        verbose_name = 'فیلینگ'
        verbose_name_plural = 'فیلینگ‌ها'


class CakeCoating(CakeOption):
    """
    طعمِ روکش — ``TEXTURES`` در custom-cake.js.

    توجه: این **طعم** روکش است، نه جنس آن. تمپلیت عمداً جنس روکش را
    نمی‌پرسد، چون بعضی طرح‌ها فقط با فوندانت اجرا می‌شوند و انتخاب مشتری
    با طرح تضاد می‌سازد. جنس را طرح تعیین می‌کند؛ همین را در مدل هم نگه
    دارید.
    """

    class Meta(CakeOption.Meta):
        verbose_name = 'روکش'
        verbose_name_plural = 'روکش‌ها'


class CakeTerm(SortableModel, ActivatableModel):
    """
    بندهای شرایط — ``TERMS`` (هشت بند در مرحله‌ی اول ویزارد).

    نسخه‌دار است چون ``CustomCakeRequest.terms_version`` باید بگوید مشتری
    کدام متن را پذیرفته. متن عوض می‌شود؛ پذیرشِ ثبت‌شده نباید عوض شود.
    """

    title = models.CharField('عنوان', max_length=120)
    text = models.TextField('متن')
    version = models.CharField('نسخه', max_length=20, default='1')

    class Meta:
        verbose_name = 'بند شرایط'
        verbose_name_plural = 'شرایط کیک اختصاصی'
        ordering = ('sort_order', 'id')

    def __str__(self):
        return self.title


# ═══════════════════════════════════════════════════════════════════
#  درخواست
# ═══════════════════════════════════════════════════════════════════

class CakeMode(models.TextChoices):
    """
    دو حالت ویزارد — ``state.mode``.

    تفاوتشان فقط ظاهری نیست: حالت چاپ هزینه‌ی جداگانه دارد و برگه‌ی
    آشپزخانه‌اش هم فرق می‌کند.
    """

    REFERENCE = 'reference', 'طرح نمونه'
    PRINT = 'print', 'چاپ عکس خوراکی'


class RequestStatus(models.TextChoices):
    SUBMITTED = 'submitted', 'ثبت شد'
    REVIEWING = 'reviewing', 'در حال بررسی'
    QUOTED = 'quoted', 'قیمت اعلام شد'
    APPROVED = 'approved', 'تأیید مشتری'
    CONVERTED = 'converted', 'تبدیل به سفارش'
    REJECTED = 'rejected', 'رد شد'
    CANCELED = 'canceled', 'لغو شد'


def generate_request_code():
    """
    ``RZ-MMDD-NNNN``.

    مثل کد سفارش، چهار رقم تصادفی به‌تنهایی یکتایی را تضمین
    نمی‌کند — اینجا حتی تنگ‌تر است چون دامنه روزانه است نه ماهانه.
    ``save()`` در صورت برخورد دوباره تلاش می‌کند.
    """
    now = timezone.localtime()
    stamp = f'{now.month:02d}{now.day:02d}'
    tail = ''.join(random.choices(string.digits, k=4))
    return f'{settings.ORDER_CODE_PREFIX}-{stamp}-{tail}'


class CustomCakeRequest(TimeStampedModel):
    """درخواست کیک اختصاصی — خروجی ویزارد پنج‌مرحله‌ای."""

    code = models.CharField(
        'کد درخواست', max_length=20, unique=True, blank=True, editable=False)

    user = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, blank=True,
        related_name='cake_requests', verbose_name='کاربر')
    order = models.ForeignKey(
        'orders.Order', on_delete=models.SET_NULL, null=True, blank=True,
        related_name='cake_requests', verbose_name='سفارش',
        help_text='وقتی پر می‌شود که درخواست به سفارش تبدیل شده باشد.')

    # ── تماس ───────────────────────────────────────────────────────
    contact_name = models.CharField('نام', max_length=60)
    contact_family = models.CharField('نام خانوادگی', max_length=60)
    contact_phone = models.CharField(
        'شماره تماس', max_length=11, validators=[validate_phone], db_index=True)
    # فرم دو شماره می‌گیرد: fPhone و fPhone2. شماره‌ی دوم برای وقتی است
    # که سفارش‌دهنده و تحویل‌گیرنده یکی نیستند، یا روز تحویل گوشی اولی
    # در دسترس نیست.
    contact_phone_alt = models.CharField(
        'شماره دوم', max_length=11, blank=True, validators=[validate_phone])
    address = models.TextField('نشانی', blank=True)

    # ── طرح ────────────────────────────────────────────────────────
    mode = models.CharField('حالت', max_length=10, choices=CakeMode.choices,
                            default=CakeMode.REFERENCE)

    size = models.ForeignKey(
        CakeSize, on_delete=models.PROTECT, related_name='requests', verbose_name='اندازه')
    flavor = models.ForeignKey(
        CakeFlavor, on_delete=models.PROTECT, related_name='requests', verbose_name='طعم')
    filling = models.ForeignKey(
        CakeFilling, on_delete=models.PROTECT, related_name='requests',
        verbose_name='فیلینگ')
    coating = models.ForeignKey(
        CakeCoating, on_delete=models.PROTECT, related_name='requests',
        verbose_name='روکش')
    occasion = models.ForeignKey(
        'catalog.Occasion', on_delete=models.SET_NULL, null=True, blank=True,
        related_name='cake_requests', verbose_name='مناسبت')

    tiers = models.SmallIntegerField('تعداد طبقه', default=1)
    color_theme = models.CharField('رنگ غالب', max_length=80, blank=True)

    message_on_cake = models.CharField(
        'نوشته روی کیک', max_length=30, blank=True,
        help_text='حداکثر ۳۰ نویسه — همان سقف ویزارد.')
    design_note = models.TextField(
        'توضیح طرح', blank=True,
        help_text='مثل عکس باشد ولی رنگ روبان‌ها صورتی…')
    allergy_note = models.TextField('حساسیت غذایی', blank=True)

    # ── زمان ───────────────────────────────────────────────────────
    event_date = models.DateField(
        'تاریخ مراسم', db_index=True,
        help_text='حداقل سه روز بعد. این شرط باید در سرور هم بررسی شود، نه فقط در تقویم.')

    # ── پول ────────────────────────────────────────────────────────
    # برآورد، نه قیمت. قیمت قطعی را سرقناد بعد از دیدن طرح اعلام می‌کند.
    estimate_min_rial = models.BigIntegerField('حداقل برآورد (ریال)', default=0)
    estimate_max_rial = models.BigIntegerField('حداکثر برآورد (ریال)', default=0)
    quoted_price_rial = models.BigIntegerField(
        'قیمت اعلام‌شده (ریال)', null=True, blank=True)

    deposit_rial = models.BigIntegerField(
        'بیعانه (ریال)', default=0,
        help_text='خالی بماند تا از جدول نرخ‌ها برداشته شود.')
    print_fee_rial = models.BigIntegerField(
        'هزینه چاپ (ریال)', default=0,
        help_text='فقط در حالت «چاپ عکس خوراکی».')

    status = models.CharField(
        'وضعیت', max_length=12, choices=RequestStatus.choices,
        default=RequestStatus.SUBMITTED, db_index=True)
    staff_note = models.TextField('یادداشت داخلی', blank=True)
    reviewed_by = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, blank=True,
        related_name='reviewed_cake_requests', verbose_name='بررسی‌کننده')

    # مهلت ۱۸ ساعته‌ی لغو. زمان قطعی ذخیره می‌شود نه محاسبه‌ی لحظه‌ای —
    # اگر بعداً مهلت را عوض کنند، درخواست‌های قبلی نباید تکان بخورند.
    cancel_deadline = models.DateTimeField('مهلت لغو', null=True, blank=True)

    # کدام نسخه از هشت بند پذیرفته شده.
    terms_accepted_at = models.DateTimeField('زمان پذیرش شرایط', null=True, blank=True)
    terms_version = models.CharField('نسخه شرایط', max_length=20, blank=True)

    class Meta:
        verbose_name = 'درخواست کیک اختصاصی'
        verbose_name_plural = 'درخواست‌های کیک اختصاصی'
        ordering = ('-created_at',)
        indexes = [
            models.Index(fields=['status', 'event_date'], name='cakereq_status_idx'),
        ]

    def __str__(self):
        return f'{self.code} — {self.full_name}'

    def clean(self):
        # همان شرطی که تقویم ویزارد اعمال می‌کند. سمت سرور هم لازم است:
        # تقویم فقط یک ورودی HTML است و با DevTools هر تاریخی می‌پذیرد.
        if self.event_date:
            soonest = timezone.localdate() + timezone.timedelta(
                days=settings.CUSTOM_CAKE_MIN_DAYS)
            if self.event_date < soonest:
                raise ValidationError({'event_date':
                    f'حداقل {settings.CUSTOM_CAKE_MIN_DAYS} روز بعد باشد '
                    f'(زودترین تاریخ ممکن: {soonest}).'})

    def save(self, *args, **kwargs):
        self.contact_phone = normalize_phone(self.contact_phone)
        self.contact_phone_alt = normalize_phone(self.contact_phone_alt)
        # نرخ‌ها در لحظه‌ی ثبت کپی می‌شوند، نه خوانده. اگر فردا بیعانه
        # بالا برود، درخواست دیروز نباید تغییر کند.
        if not self.deposit_rial or (self.mode == CakeMode.PRINT
                                     and not self.print_fee_rial):
            pricing = Pricing.load()
            if not self.deposit_rial:
                self.deposit_rial = pricing.custom_deposit_rial
            if self.mode == CakeMode.PRINT and not self.print_fee_rial:
                self.print_fee_rial = pricing.custom_print_fee_rial
        if not self.cancel_deadline:
            self.cancel_deadline = timezone.now() + timezone.timedelta(
                hours=settings.CUSTOM_CAKE_CANCEL_HOURS)
        if self.code:
            super().save(*args, **kwargs)
            return
        save_with_unique_code(self, generate_request_code, super().save,
                              *args, **kwargs)

    @property
    def full_name(self):
        return f'{self.contact_name} {self.contact_family}'.strip()

    @property
    def can_cancel(self):
        """
        مهلت لغوِ مشتری (۱۸ ساعت).

        درخواستی که بیعانه‌اش رسیده بی‌درنگ به سفارش آشپزخانه تبدیل
        می‌شود؛ این تبدیل نباید حق لغو را بگیرد. تا وقتی مهلت نگذشته و
        پخت شروع نشده، هنوز می‌شود لغو کرد.
        """
        if not self.cancel_deadline or timezone.now() >= self.cancel_deadline:
            return False
        if self.status in (RequestStatus.SUBMITTED, RequestStatus.REVIEWING):
            return True
        if self.status != RequestStatus.CONVERTED:
            return False
        from apps.orders.models import FulfillmentStatus
        return self.order is None or self.order.fulfillment_status == FulfillmentStatus.NEW

    @property
    def reference_images(self):
        return [image for image in self.images.all()
                if image.kind == CakeImageKind.REFERENCE]

    @property
    def print_image(self):
        for image in self.images.all():
            if image.kind == CakeImageKind.PRINT:
                return image
        return None


class CakeImageKind(models.TextChoices):
    """
    دو نوع تصویر که به‌هیچ‌وجه یکی نیستند.

    ``REFERENCE`` عکس نمونه است: «برای الهام فرستادم، عیناً کپی نشود».
    ``PRINT`` عکسی است که **روی کیک چاپ می‌شود** — معمولاً عکس خانوادگی،
    با یادداشت جداگانه («چاپ روی کاغذ خوراکی»).

    یکی گرفتنشان یعنی روزی عکس اشتباهی روی کیک عروسی کسی چاپ می‌شود.
    """

    REFERENCE = 'reference', 'عکس نمونه'
    PRINT = 'print', 'عکس چاپ روی کیک'


class CustomCakeImage(models.Model):
    """
    تصویر آپلودی مشتری.

    زیر ``PRIVATE_MEDIA_ROOT`` ذخیره می‌شود، نه ``MEDIA_ROOT``: این‌ها
    گاهی عکس خانوادگی‌اند و نباید با حدس‌زدن URL قابل دیدن باشند. فقط یک
    ویوی مجوزدار می‌خواندشان — صاحب درخواست، ادمین قنادی، مدیر.
    """

    request = models.ForeignKey(
        CustomCakeRequest, on_delete=models.CASCADE,
        related_name='images', verbose_name='درخواست')

    image = ImageField(
        'تصویر', upload_to=upload.custom_cake_image,
        storage=private_storage, validators=[validate_image_size])
    kind = models.CharField(
        'نوع', max_length=10, choices=CakeImageKind.choices,
        default=CakeImageKind.REFERENCE)

    caption = models.CharField(
        'یادداشت', max_length=200, blank=True,
        help_text='refNote یا printNote — «مشتری گفت: …»')
    sort_order = models.SmallIntegerField('ترتیب', default=0)

    # نوع واقعی فایل سمت سرور تشخیص داده می‌شود، نه از روی پسوند: یک
    # اسکریپت با نام ‎.jpg‎ هنوز اسکریپت است.
    content_type = models.CharField('نوع فایل', max_length=60, blank=True)
    size_bytes = models.IntegerField('حجم', default=0)

    uploaded_at = models.DateTimeField('زمان آپلود', auto_now_add=True)

    class Meta:
        verbose_name = 'تصویر کیک اختصاصی'
        verbose_name_plural = 'تصاویر کیک اختصاصی'
        ordering = ('kind', 'sort_order', 'id')

    def __str__(self):
        return f'{self.request.code} — {self.get_kind_display()}'

