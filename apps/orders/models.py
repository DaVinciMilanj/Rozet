"""
سبد، بازه‌ی تحویل، کد تخفیف، سفارش و فاکتور.

منبع در تمپلیت:
    js/cart.js                 RozetCart
    checkout/checkout.js       SLOTS · PROMOS · SHIP_FEE · GIFT_FEE · payload
    admin/data/orders-data.js  STATE · PREV · ORDERS · items · spec
    account/account.js         SEED.orders
"""

import random
import string

from django.conf import settings
from django.core.exceptions import ValidationError
from django.core.validators import MinValueValidator
from django.db import models
from django.db.models import Q
from django.utils import timezone

from apps.common.fields import ImageField, JSONField
from apps.common.models import TimeStampedModel, save_with_unique_code
from apps.common.text import normalize_phone
from apps.common.validators import validate_phone
from apps.common import upload


# ═══════════════════════════════════════════════════════════════════
#  سبد خرید
# ═══════════════════════════════════════════════════════════════════

class Cart(TimeStampedModel):
    """
    سبد خرید.

    در تمپلیت سبد در ``localStorage`` است، یعنی قیمتش با DevTools قابل
    ویرایش. اینجا سبد فقط **شناسه‌ها** را نگه می‌دارد؛ هیچ مبلغی ذخیره
    نمی‌شود و جمع در هر بار از روی دیتابیس ساخته می‌شود.

    مهمان هم سبد دارد (با ``session_key``). موقع ورود، سبد نشست به سبد
    کاربر ادغام می‌شود.
    """

    user = models.OneToOneField(
        settings.AUTH_USER_MODEL, on_delete=models.CASCADE, null=True, blank=True,
        related_name='cart', verbose_name='کاربر')
    session_key = models.CharField(
        'کلید نشست', max_length=40, blank=True, db_index=True)

    class Meta:
        verbose_name = 'سبد خرید'
        verbose_name_plural = 'سبدهای خرید'
        constraints = [
            models.CheckConstraint(
                condition=Q(user__isnull=False) | ~Q(session_key=''),
                name='cart_has_owner'),
        ]

    def __str__(self):
        return f'سبد {self.user or self.session_key[:8]}'

    @property
    def items_total_rial(self):
        return sum(item.line_total_rial for item in self.items.all())

    @property
    def count(self):
        return sum(item.quantity for item in self.items.all())


class CartItem(TimeStampedModel):
    """
    قلم سبد.

    ``addons`` رابطه‌ی چندبه‌چند است نه فهرست شناسه در JSON: یک شناسه‌ی
    نامعتبر در JSON تا لحظه‌ی محاسبه‌ی قیمت کشف نمی‌شود، ولی کلید خارجی
    همان‌جا رد می‌شود.
    """

    cart = models.ForeignKey(
        Cart, on_delete=models.CASCADE, related_name='items', verbose_name='سبد')
    product = models.ForeignKey(
        'catalog.Product', on_delete=models.CASCADE, verbose_name='محصول')
    size = models.ForeignKey(
        'catalog.ProductSize', on_delete=models.SET_NULL, null=True, blank=True,
        verbose_name='اندازه')
    flavor = models.ForeignKey(
        'catalog.ProductFlavor', on_delete=models.SET_NULL, null=True, blank=True,
        verbose_name='طعم')
    addons = models.ManyToManyField(
        'catalog.ProductAddon', blank=True, verbose_name='افزودنی‌ها')

    message_on_cake = models.CharField('نوشته روی کیک', max_length=60, blank=True)
    quantity = models.SmallIntegerField('تعداد', default=1, validators=[MinValueValidator(1)])

    class Meta:
        verbose_name = 'قلم سبد'
        verbose_name_plural = 'اقلام سبد'
        ordering = ('created_at',)
        constraints = [
            models.CheckConstraint(
                condition=Q(quantity__gte=1), name='cartitem_quantity_positive'),
        ]

    def __str__(self):
        return f'{self.product.name} ×{self.quantity}'

    @property
    def unit_price_rial(self):
        """
        قیمت واحد از روی دیتابیس، نه از روی چیزی که مرورگر فرستاده.

        اندازه و طعم باید متعلق به همین محصول باشند — وگرنه می‌شود با
        دست‌کاری فرم، اختلاف قیمتِ منفیِ محصول دیگری را روی این بست.
        """
        price = self.product.price_rial
        if self.size_id and self.size.product_id == self.product_id:
            price += self.size.price_delta_rial
        if self.flavor_id and self.flavor.product_id == self.product_id:
            price += self.flavor.price_delta_rial
        for addon in self.addons.all():
            if addon.product_id == self.product_id:
                price += addon.price_delta_rial
        return price

    @property
    def line_total_rial(self):
        return self.unit_price_rial * self.quantity


# ═══════════════════════════════════════════════════════════════════
#  بازه‌ی تحویل
# ═══════════════════════════════════════════════════════════════════

class DeliverySlot(models.Model):
    """
    بازه‌ی ساعتی تحویل — SLOTS در checkout.js (۱۱ تا ۲۱، پنج بازه).

    ``capacity`` عددِ آشپزخانه است: چند سفارش در این بازه می‌شود آماده
    کرد. بدون آن، تمام سفارش‌های شنبه می‌توانند روی یک بازه بنشینند.
    """

    label = models.CharField('عنوان', max_length=40, help_text='۱۱ تا ۱۳')
    start_time = models.TimeField('از ساعت')
    end_time = models.TimeField('تا ساعت')

    weekday = models.SmallIntegerField(
        'روز هفته', null=True, blank=True,
        help_text='خالی یعنی همه‌ی روزها. ۰ شنبه تا ۶ جمعه.')

    capacity = models.SmallIntegerField('ظرفیت', default=10)
    is_active = models.BooleanField('فعال', default=True)
    sort_order = models.SmallIntegerField('ترتیب', default=0)

    class Meta:
        verbose_name = 'بازه تحویل'
        verbose_name_plural = 'بازه‌های تحویل'
        ordering = ('sort_order', 'start_time')

    def __str__(self):
        return self.label

    def clean(self):
        if self.start_time and self.end_time and self.end_time <= self.start_time:
            raise ValidationError({'end_time': 'باید بعد از ساعت شروع باشد.'})

    def booked_on(self, date):
        """
        چند سفارش زنده روی این بازه در این روز نشسته است.

        شمارنده‌ی جداگانه‌ای نگه داشته نمی‌شود: یک ``COUNT`` روی ستون
        ایندکس‌شده‌ی ``due_date`` برای قنادی‌ای با ده‌ها سفارش در روز
        رایگان است، و شمارنده‌ی ذخیره‌شده دو دردسر دارد — باید اتمی نگه
        داشته شود، و با هر لغو سفارش از حقیقت جدا می‌افتد.
        """
        return self.orders.filter(due_date=date).exclude(
            fulfillment_status=FulfillmentStatus.CANCELED).count()

    def is_full_on(self, date):
        return self.booked_on(date) >= self.capacity


# ═══════════════════════════════════════════════════════════════════
#  کد تخفیف
# ═══════════════════════════════════════════════════════════════════

class PromoKind(models.TextChoices):
    PERCENT = 'percent', 'درصدی'
    FIXED = 'fixed', 'مبلغ ثابت'


class PromoCode(TimeStampedModel):
    """
    کد تخفیف — ``PROMOS`` در checkout.js.

    در تمپلیت دو کد ثابت در جاوااسکریپت‌اند: ``ROZET10`` و ``شیرین``. کد
    فارسی هم داریم، پس یکتایی باید بدون حساسیت به حروف و روی شکل
    نرمال‌شده باشد.
    """

    code = models.CharField('کد', max_length=40, unique=True)
    description = models.CharField('توضیح', max_length=120, blank=True)

    kind = models.CharField('نوع', max_length=10, choices=PromoKind.choices,
                            default=PromoKind.PERCENT)
    value = models.IntegerField(
        'مقدار', help_text='برای درصدی عدد ۱ تا ۱۰۰؛ برای مبلغ ثابت، ریال.')

    min_order_rial = models.BigIntegerField('حداقل مبلغ سفارش (ریال)', default=0)
    max_discount_rial = models.BigIntegerField(
        'سقف تخفیف (ریال)', null=True, blank=True,
        help_text='برای تخفیف درصدی حتماً پر شود.')

    starts_at = models.DateTimeField('شروع', null=True, blank=True)
    ends_at = models.DateTimeField('پایان', null=True, blank=True)

    total_limit = models.IntegerField('سقف کل استفاده', null=True, blank=True)
    per_user_limit = models.SmallIntegerField('سقف هر کاربر', default=1)
    used_count = models.IntegerField('تعداد استفاده', default=0)

    first_order_only = models.BooleanField('فقط اولین سفارش', default=False)
    is_active = models.BooleanField('فعال', default=True)

    class Meta:
        verbose_name = 'کد تخفیف'
        verbose_name_plural = 'کدهای تخفیف'
        ordering = ('-created_at',)

    def __str__(self):
        return self.code

    def save(self, *args, **kwargs):
        self.code = self.code.strip()
        super().save(*args, **kwargs)

    def clean(self):
        errors = {}
        if self.kind == PromoKind.PERCENT:
            if not 1 <= (self.value or 0) <= 100:
                errors['value'] = 'تخفیف درصدی باید بین ۱ تا ۱۰۰ باشد.'
            if not self.max_discount_rial:
                # بدون سقف، ۲۰٪ روی یک سفارش ده‌میلیونی دو میلیون تومان
                # تخفیف می‌دهد و کسی تا آخر ماه متوجه نمی‌شود.
                errors['max_discount_rial'] = 'برای تخفیف درصدی، سقف الزامی است.'
        elif (self.value or 0) <= 0:
            errors['value'] = 'مبلغ تخفیف باید بیشتر از صفر باشد.'

        if self.starts_at and self.ends_at and self.ends_at <= self.starts_at:
            errors['ends_at'] = 'باید بعد از تاریخ شروع باشد.'
        if errors:
            raise ValidationError(errors)

    def discount_for(self, amount_rial):
        """مبلغ تخفیف روی این جمع — با رعایت سقف."""
        if self.kind == PromoKind.FIXED:
            discount = min(self.value, amount_rial)
        else:
            discount = amount_rial * self.value // 100
        if self.max_discount_rial:
            discount = min(discount, self.max_discount_rial)
        return max(0, discount)

    @property
    def is_running(self):
        now = timezone.now()
        if not self.is_active:
            return False
        if self.starts_at and now < self.starts_at:
            return False
        if self.ends_at and now > self.ends_at:
            return False
        if self.total_limit is not None and self.used_count >= self.total_limit:
            return False
        return True


# ═══════════════════════════════════════════════════════════════════
#  سفارش
# ═══════════════════════════════════════════════════════════════════

class FulfillmentStatus(models.TextChoices):
    """
    وضعیت آشپزخانه — ``STATE`` در orders-data.js.

    گذار روبه‌جلو با دکمه‌ی اصلی کارت، و گذار روبه‌عقب با دکمه‌ی «برگرد»
    (``PREV``). هر دو مجازند؛ فقط معکوس باید محدود به مدیر باشد و حتماً
    در تاریخچه ثبت شود.
    """

    NEW = 'new', 'ثبت شد'
    BAKING = 'baking', 'در حال پخت'
    READY = 'ready', 'آماده'
    DELIVERED = 'delivered', 'تحویل شد'
    CANCELED = 'canceled', 'لغو شد'


class PaymentStatus(models.TextChoices):
    """
    وضعیت مالی — مستقل از وضعیت آشپزخانه.

    داده‌ی خود تمپلیت این را لازم می‌کند: کنار ``status`` یک ``total`` و
    یک ``paid`` جدا دارد. ``paid: 400000`` در برابر ``total: 620000`` یعنی
    «در حال پخت، با ۲۲۰ هزار تومان مانده» — یک ستون این را نمی‌گوید.
    """

    UNPAID = 'unpaid', 'پرداخت نشده'
    DEPOSIT = 'deposit', 'بیعانه'
    PAID = 'paid', 'پرداخت شده'
    REFUNDED = 'refunded', 'بازگشت داده شد'
    FAILED = 'failed', 'ناموفق'


class DeliveryMethod(models.TextChoices):
    PICKUP = 'pickup', 'تحویل حضوری'
    COURIER = 'courier', 'ارسال با پیک'


class PayMethod(models.TextChoices):
    ONLINE = 'online', 'پرداخت آنلاین'
    ONSITE = 'onsite', 'پرداخت در محل'


# گذارهای مجاز. هر تغییر وضعیتی که اینجا نیست، رد می‌شود.
FORWARD_TRANSITIONS = {
    FulfillmentStatus.NEW: (FulfillmentStatus.BAKING, FulfillmentStatus.CANCELED),
    FulfillmentStatus.BAKING: (FulfillmentStatus.READY, FulfillmentStatus.CANCELED),
    FulfillmentStatus.READY: (FulfillmentStatus.DELIVERED, FulfillmentStatus.CANCELED),
    FulfillmentStatus.DELIVERED: (),
    FulfillmentStatus.CANCELED: (),
}

# دکمه‌ی «برگرد» — PREV در orders-data.js
BACKWARD_TRANSITIONS = {
    FulfillmentStatus.BAKING: FulfillmentStatus.NEW,
    FulfillmentStatus.READY: FulfillmentStatus.BAKING,
    FulfillmentStatus.DELIVERED: FulfillmentStatus.READY,
}


class OrderQuerySet(models.QuerySet):
    def open(self):
        return self.exclude(fulfillment_status__in=(
            FulfillmentStatus.DELIVERED, FulfillmentStatus.CANCELED))

    def overdue(self):
        """
        عقب‌افتاده‌های تابلو.

        ستون ذخیره‌شده نیست و نباید باشد: «عقب‌افتاده» تابعی از تاریخ
        امروز است و هر شب باید خودش عوض شود.
        """
        return self.open().filter(due_date__lt=timezone.localdate())

    def due_today(self):
        return self.open().filter(due_date=timezone.localdate())

    def upcoming(self):
        return self.open().filter(due_date__gt=timezone.localdate())

    def for_board(self):
        return self.select_related('user', 'slot').prefetch_related('items')


def generate_order_code():
    """
    ``RZ-YYMM-NNNN``.

    تمپلیت دو قالب داشت (``RZ-140419`` و ``RZ-2609-4471``)؛ این یکی
    انتخاب شد چون هم ماه را نشان می‌دهد و هم چهار رقم تصادفی دارد، پس
    تعداد سفارش‌های ماه از روی کد قابل حدس نیست.

    چهار رقم یعنی ۱۰٬۰۰۰ حالت در ماه، و به حکم پارادوکس تولد با
    ۱۲۰ سفارش در ماه احتمال برخورد ۵۰٪ است. پس این تابع به تنهایی
    کافی نیست و ``Order.save()`` در صورت تکرار دوباره تلاش می‌کند.
    """
    now = timezone.localtime()
    stamp = f'{now.year % 100:02d}{now.month:02d}'
    tail = ''.join(random.choices(string.digits, k=4))
    return f'{settings.ORDER_CODE_PREFIX}-{stamp}-{tail}'


class Order(TimeStampedModel):
    """سفارش ثبت‌شده."""

    code = models.CharField(
        'کد سفارش', max_length=20, unique=True, blank=True, editable=False)

    # SET_NULL نه CASCADE: سفارش مهمان وجود دارد، و حذف حساب نباید سند
    # مالی را ببرد.
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, blank=True,
        related_name='orders', verbose_name='کاربر')

    # اسنپ‌شات: آشپزخانه باید بتواند تماس بگیرد حتی اگر کاربر بعداً
    # شماره‌اش را عوض کند یا حساب را ببندد.
    customer_name = models.CharField('نام مشتری', max_length=120)
    customer_phone = models.CharField(
        'شماره مشتری', max_length=11, validators=[validate_phone], db_index=True)

    method = models.CharField(
        'روش تحویل', max_length=10, choices=DeliveryMethod.choices,
        default=DeliveryMethod.PICKUP)

    # تنها JSON مجاز در این مدل: یک عکسِ ثابت از نشانی در لحظه‌ی ثبت.
    # چیزی که بعداً ویرایش یا کوئری شود، ستون یا جدول می‌خواهد نه JSON.
    address_snapshot = JSONField('نشانی (اسنپ‌شات)', default=dict, blank=True)

    due_date = models.DateField('تاریخ تحویل', db_index=True)
    slot = models.ForeignKey(
        DeliverySlot, on_delete=models.SET_NULL, null=True, blank=True,
        related_name='orders', verbose_name='بازه تحویل')

    fulfillment_status = models.CharField(
        'وضعیت آماده‌سازی', max_length=12, choices=FulfillmentStatus.choices,
        default=FulfillmentStatus.NEW, db_index=True)
    payment_status = models.CharField(
        'وضعیت پرداخت', max_length=10, choices=PaymentStatus.choices,
        default=PaymentStatus.UNPAID, db_index=True)
    pay_method = models.CharField(
        'روش پرداخت', max_length=10, choices=PayMethod.choices, default=PayMethod.ONLINE)

    # همه به ریال
    items_total_rial = models.BigIntegerField('جمع اقلام (ریال)', default=0)
    discount_rial = models.BigIntegerField('تخفیف (ریال)', default=0)
    delivery_fee_rial = models.BigIntegerField('هزینه ارسال (ریال)', default=0)
    gift_wrap_rial = models.BigIntegerField('بسته هدیه (ریال)', default=0)
    vat_rial = models.BigIntegerField('مالیات (ریال)', default=0)
    grand_total_rial = models.BigIntegerField('مبلغ نهایی (ریال)', default=0)
    paid_rial = models.BigIntegerField('پرداخت‌شده (ریال)', default=0)

    # نرخ مالیات در لحظه‌ی ثبت کپی می‌شود. تغییر نرخ در سال آینده نباید
    # فاکتور امسال را عوض کند.
    vat_percent = models.DecimalField('نرخ مالیات', max_digits=5, decimal_places=2,
                                      default=0)

    promo = models.ForeignKey(
        PromoCode, on_delete=models.SET_NULL, null=True, blank=True,
        related_name='orders', verbose_name='کد تخفیف')

    gift_wrap = models.BooleanField('بسته‌بندی هدیه', default=False)
    gift_message = models.TextField('پیام کارت هدیه', blank=True)

    allergy_note = models.TextField(
        'حساسیت غذایی', blank=True,
        help_text='روی کارت تابلو با هشدار قرمز نشان داده می‌شود.')
    customer_note = models.TextField('یادداشت مشتری', blank=True)
    staff_note = models.TextField('یادداشت داخلی', blank=True)

    placed_at = models.DateTimeField('زمان ثبت', default=timezone.now, db_index=True)
    ready_at = models.DateTimeField('زمان آماده شدن', null=True, blank=True)
    delivered_at = models.DateTimeField('زمان تحویل', null=True, blank=True)
    canceled_at = models.DateTimeField('زمان لغو', null=True, blank=True)
    canceled_by = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, blank=True,
        related_name='canceled_orders', verbose_name='لغو توسط')
    cancel_reason = models.CharField('دلیل لغو', max_length=200, blank=True)

    # قفل خوش‌بینانه. دو نفر از آشپزخانه ممکن است همزمان روی یک سفارش
    # بزنند؛ بدون این، تغییر دومی اولی را بی‌صدا پاک می‌کند.
    version = models.IntegerField('نسخه', default=1)

    objects = OrderQuerySet.as_manager()

    class Meta:
        verbose_name = 'سفارش'
        verbose_name_plural = 'سفارش‌ها'
        ordering = ('-placed_at',)
        indexes = [
            models.Index(fields=['fulfillment_status', 'due_date'], name='order_board_idx'),
            models.Index(fields=['user', '-placed_at'], name='order_user_idx'),
            models.Index(fields=['payment_status', '-placed_at'], name='order_pay_idx'),
            # تابلوی آشپزخانه فقط سفارش‌های باز را می‌خواند.
            models.Index(
                fields=['due_date'],
                condition=~Q(fulfillment_status__in=['delivered', 'canceled']),
                name='order_open_due_idx'),
        ]
        constraints = [
            models.CheckConstraint(
                condition=Q(grand_total_rial__gte=0), name='order_total_non_negative'),
            models.CheckConstraint(
                condition=Q(paid_rial__gte=0), name='order_paid_non_negative'),
        ]

    def __str__(self):
        return self.code

    # ── شمارنده‌های باشگاه ─────────────────────────────────────────
    #
    # وضعیتِ خوانده‌شده از دیتابیس نگه داشته می‌شود تا save() بفهمد گذار
    # «همین الان» اتفاق افتاده یا سفارش از قبل تحویل‌شده بوده.
    #
    # چرا سیگنال نه: ``post_save`` مقدار قبلی را نمی‌بیند و ``pre_save``
    # برای دیدنش باید یک کوئری اضافه بزند. ``from_db`` رایگان است — مقدار
    # همان لحظه که ردیف خوانده می‌شود در دست است.

    @classmethod
    def from_db(cls, db, field_names, values):
        instance = super().from_db(db, field_names, values)
        instance._was_delivered = (
            instance.fulfillment_status == FulfillmentStatus.DELIVERED)
        return instance

    def save(self, *args, **kwargs):
        self.customer_phone = normalize_phone(self.customer_phone)
        if self.code:
            super().save(*args, **kwargs)
        else:
            save_with_unique_code(self, generate_order_code, super().save,
                                  *args, **kwargs)
        self._sync_loyalty()

    def _sync_loyalty(self):
        """
        با هر گذار به «تحویل شد» شمارنده بالا و با برگشتش پایین می‌رود.

        دکمه‌ی «برگرد» تابلو یعنی این گذار معکوس هم می‌شود؛ بدون کم‌کردن،
        یک اشتباهِ ساده‌ی آشپزخانه مشتری را برای همیشه یک پله جلو می‌برد.

        با ``F()`` نوشته می‌شود تا دو سفارشِ همزمان همدیگر را پاک نکنند.
        """
        was = getattr(self, '_was_delivered', False)
        now = self.fulfillment_status == FulfillmentStatus.DELIVERED
        if was == now or not self.user_id:
            self._was_delivered = now
            return

        step, amount = (1, self.grand_total_rial) if now else (-1, -self.grand_total_rial)
        fields = {
            'orders_count': models.F('orders_count') + step,
            'total_spent_rial': models.F('total_spent_rial') + amount,
        }
        if now:
            fields['last_order_at'] = self.delivered_at or timezone.now()
        type(self.user).objects.filter(pk=self.user_id).update(**fields)
        self._was_delivered = now

    # ── وضعیت ──────────────────────────────────────────────────────

    @property
    def is_open(self):
        return self.fulfillment_status not in (
            FulfillmentStatus.DELIVERED, FulfillmentStatus.CANCELED)

    @property
    def is_overdue(self):
        return self.is_open and self.due_date < timezone.localdate()

    @property
    def days_from_today(self):
        """منفی یعنی عقب‌افتاده — ``daysFromToday()`` در orders-data.js."""
        return (self.due_date - timezone.localdate()).days

    @property
    def next_status(self):
        forward = FORWARD_TRANSITIONS.get(self.fulfillment_status, ())
        return forward[0] if forward else None

    @property
    def previous_status(self):
        return BACKWARD_TRANSITIONS.get(self.fulfillment_status)

    def can_move_to(self, status):
        return status in FORWARD_TRANSITIONS.get(self.fulfillment_status, ())

    # ── مالی ───────────────────────────────────────────────────────

    @property
    def remaining_rial(self):
        return max(0, self.grand_total_rial - self.paid_rial)

    @property
    def is_settled(self):
        return self.paid_rial >= self.grand_total_rial

    @property
    def has_custom_item(self):
        return any(item.kind == OrderItemKind.CUSTOM for item in self.items.all())


class OrderItemKind(models.TextChoices):
    CATALOGUE = 'catalogue', 'ویترین'
    CUSTOM = 'custom', 'سفارشی'


class OrderItem(models.Model):
    """
    قلم سفارش — اسنپ‌شات کامل.

    نام و اندازه و قیمت کپی می‌شوند، نه اینکه از محصول خوانده شوند. اگر
    فردا قیمت محصول عوض شود، فاکتور دیروز نباید تغییر کند؛ فاکتور سند
    مالی است نه یک نمای زنده.
    """

    order = models.ForeignKey(
        Order, on_delete=models.CASCADE, related_name='items', verbose_name='سفارش')
    kind = models.CharField(
        'نوع', max_length=10, choices=OrderItemKind.choices,
        default=OrderItemKind.CATALOGUE)

    product = models.ForeignKey(
        'catalog.Product', on_delete=models.SET_NULL, null=True, blank=True,
        related_name='order_items', verbose_name='محصول')
    custom_cake = models.ForeignKey(
        'custom_cake.CustomCakeRequest', on_delete=models.SET_NULL, null=True, blank=True,
        related_name='order_items', verbose_name='کیک اختصاصی')

    name = models.CharField('نام', max_length=140)
    size_label = models.CharField('اندازه', max_length=80, blank=True)
    flavor_label = models.CharField('طعم', max_length=80, blank=True)
    image = ImageField(
        'تصویر', upload_to=upload.order_item_image, blank=True,
        help_text='اسنپ‌شات تصویر؛ محصول ممکن است سال‌ها بعد عوض شود.')

    message_on_cake = models.CharField(
        'نوشته روی کیک', max_length=60, blank=True,
        help_text='«روی کیک نوشته شود: …» — write در orders-data.js')

    quantity = models.SmallIntegerField('تعداد', default=1, validators=[MinValueValidator(1)])
    unit_price_rial = models.BigIntegerField('قیمت واحد (ریال)')
    line_total_rial = models.BigIntegerField('جمع ردیف (ریال)')

    class Meta:
        verbose_name = 'قلم سفارش'
        verbose_name_plural = 'اقلام سفارش'
        ordering = ('id',)
        constraints = [
            models.CheckConstraint(
                condition=Q(quantity__gte=1), name='orderitem_quantity_positive'),
        ]

    def __str__(self):
        return f'{self.name} ×{self.quantity}'


class OrderItemSpec(models.Model):
    """
    مشخصات آزاد یک قلم — ``spec: [{l, v}]`` در orders-data.js.

    این همان برگه‌ای است که سرقناد می‌خواند: «طبقه: دو طبقه»، «رنگ غالب:
    کِرِم و طلایی»، «تزئین: گل خوراکی و ورق طلا».

    عمداً برچسب/مقدارِ آزاد است و ستون ثابت ندارد: تمپلیت هم روی قلم
    ویترینی یک نکته می‌گذارد («مرنگ همان روز برشته شود») و هم روی کیک
    اختصاصی هشت سطر مشخصات. هر تلاشی برای ستون‌کردن، یکی از این دو را
    می‌شکند.

    و چرا JSONField نه: ``default=list, blank=True`` وقتی فرم خالی بماند
    ``None`` می‌فرستد و ``NOT NULL constraint failed`` می‌دهد.
    """

    item = models.ForeignKey(
        OrderItem, on_delete=models.CASCADE, related_name='specs', verbose_name='قلم')
    label = models.CharField('برچسب', max_length=60)
    value = models.CharField('مقدار', max_length=300)
    sort_order = models.SmallIntegerField('ترتیب', default=0)

    class Meta:
        verbose_name = 'مشخصه قلم'
        verbose_name_plural = 'مشخصات قلم'
        ordering = ('sort_order', 'id')

    def __str__(self):
        return f'{self.label}: {self.value}'


class OrderStatusHistory(models.Model):
    """
    تاریخچه‌ی تغییر وضعیت — تایم‌لاین صفحه‌ی جزئیات و دکمه‌ی «برگرد».

    وقتی سر یک سفارش اختلاف پیش بیاید، تنها چیزی که حرف می‌زند همین
    جدول است.
    """

    class Field(models.TextChoices):
        FULFILLMENT = 'fulfillment', 'آماده‌سازی'
        PAYMENT = 'payment', 'پرداخت'

    order = models.ForeignKey(
        Order, on_delete=models.CASCADE, related_name='history', verbose_name='سفارش')
    field = models.CharField('ستون', max_length=12, choices=Field.choices,
                             default=Field.FULFILLMENT)
    from_value = models.CharField('از', max_length=12, blank=True)
    to_value = models.CharField('به', max_length=12)

    changed_by = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, blank=True,
        related_name='order_changes', verbose_name='توسط')
    is_reverse = models.BooleanField('بازگشت به عقب', default=False)
    note = models.CharField('یادداشت', max_length=200, blank=True)
    changed_at = models.DateTimeField('زمان', auto_now_add=True, db_index=True)

    class Meta:
        verbose_name = 'تغییر وضعیت'
        verbose_name_plural = 'تاریخچه وضعیت'
        ordering = ('changed_at',)

    def __str__(self):
        return f'{self.order.code}: {self.from_value} → {self.to_value}'
