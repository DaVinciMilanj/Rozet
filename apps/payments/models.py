"""
پرداخت و بازگشت وجه.

درگاه آنلاین فقط زرین‌پال است. اتصال واقعی فعلاً انجام نمی‌شود؛
این مدل ساختارِ آماده است تا وقتی نماد اعتماد گرفته شد، فقط یک
کلاینت به آن وصل شود.

منبع در تمپلیت:
    admin/data/orders-data.js   payMethod · paid · total
    checkout/checkout.js        pay: 'online' | 'onsite'
"""

from django.conf import settings
from django.db import models

from apps.common.fields import JSONField
from apps.common.models import TimeStampedModel


class Gateway(models.TextChoices):
    """
    پول از کدام کانال رسیده است.

    درگاه آنلاین فقط **زرین‌پال** است و قرار نیست بیشتر شود، پس هیچ
    «انتخاب درگاه»ی در کار نیست. بقیه‌ی گزینه‌ها درگاه نیستند؛ راه‌های
    دریافت حضوری‌اند که کارکنان دستی ثبت می‌کنند.

    این با ``Order.pay_method`` فرق دارد: آن‌جا **انتخاب مشتری** است
    (آنلاین یا در محل)، اینجا **واقعیتِ دریافت**.
    """

    ZARINPAL = 'zarinpal', 'زرین‌پال'
    CASH = 'cash', 'نقدی'
    CARD = 'card', 'کارت‌خوان'
    TRANSFER = 'transfer', 'کارت به کارت'
    # تا وقتی درگاه واقعی وصل نشده، پرداخت‌ها با این کانال ثبت می‌شوند.
    # جدا نگه داشتنشان عمدی است: در گزارش مالی باید بشود این ردیف‌ها را
    # از پول واقعی تشخیص داد و کنار گذاشت.
    SANDBOX = 'sandbox', 'بدون درگاه (آزمایشی)'


class PaymentKind(models.TextChoices):
    """
    کیک اختصاصی دومرحله‌ای پرداخت می‌شود: بیعانه، بعد تسویه.

    برای همین ``Payment`` رابطه‌ی چندبه‌یک با سفارش دارد نه یک‌به‌یک — یک
    سفارش چند پرداخت دارد.
    """

    FULL = 'full', 'پرداخت کامل'
    DEPOSIT = 'deposit', 'بیعانه'
    SETTLEMENT = 'settlement', 'تسویه مانده'
    # بازگشت وجه جدول جدا نمی‌خواهد: یک تراکنش است با مبلغ منفی،
    # روی همان سفارش و با همان ستون‌های پیگیری.
    REFUND = 'refund', 'بازگشت وجه'


class PaymentState(models.TextChoices):
    PENDING = 'pending', 'در انتظار'
    SUCCEEDED = 'succeeded', 'موفق'
    FAILED = 'failed', 'ناموفق'
    CANCELED = 'canceled', 'لغو شده'


class Payment(TimeStampedModel):
    """
    یک تراکنش.

    مبلغ به ریال است — همان واحدی که درگاه‌های ایرانی می‌گیرند. تبدیل از
    تومان فقط در لحظه‌ی نمایش انجام می‌شود، هرگز در مسیر پرداخت.
    """

    # یکی از این دو پر است، نه هر دو و نه هیچ‌کدام — قید پایین.
    # بیعانه‌ی کیک اختصاصی پیش از ساخت سفارش گرفته می‌شود (قیمت قطعی
    # هنوز اعلام نشده)، پس نمی‌تواند به سفارش وصل باشد.
    order = models.ForeignKey(
        'orders.Order', on_delete=models.PROTECT, null=True, blank=True,
        related_name='payments', verbose_name='سفارش')
    custom_cake = models.ForeignKey(
        'custom_cake.CustomCakeRequest', on_delete=models.PROTECT,
        null=True, blank=True, related_name='payments',
        verbose_name='درخواست کیک اختصاصی')

    gateway = models.CharField('کانال دریافت', max_length=12,
                               choices=Gateway.choices, default=Gateway.ZARINPAL)
    kind = models.CharField('نوع', max_length=12, choices=PaymentKind.choices,
                            default=PaymentKind.FULL)
    amount_rial = models.BigIntegerField('مبلغ (ریال)')
    status = models.CharField('وضعیت', max_length=10, choices=PaymentState.choices,
                              default=PaymentState.PENDING, db_index=True)

    authority = models.CharField('شناسه تراکنش درگاه', max_length=120, blank=True,
                                 db_index=True)
    ref_id = models.CharField('کد پیگیری', max_length=80, blank=True)
    card_pan = models.CharField('شماره کارت (ماسک‌شده)', max_length=24, blank=True)

    # پاسخ خام درگاه. وقتی سر یک تراکنش اختلاف پیش بیاید، این تنها سندی
    # است که وجود دارد — هیچ‌وقت پاک نشود.
    raw_response = JSONField('پاسخ درگاه', default=dict, blank=True)

    paid_at = models.DateTimeField('زمان پرداخت', null=True, blank=True)
    # برای پرداخت نقدی و کارت‌خوان: چه کسی ثبت کرد که پول را گرفته است.
    recorded_by = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, blank=True,
        related_name='recorded_payments', verbose_name='ثبت توسط')
    note = models.CharField('توضیح', max_length=200, blank=True,
                            help_text='برای بازگشت وجه، دلیلش را اینجا بنویسید.')

    class Meta:
        verbose_name = 'پرداخت'
        verbose_name_plural = 'پرداخت‌ها'
        ordering = ('-created_at',)
        constraints = [
            # callback درگاه گاهی دو بار می‌آید. بدون این قید، یک پرداخت
            # دو بار روی سفارش می‌نشیند و مبلغ پرداخت‌شده دو برابر
            # می‌شود.
            models.UniqueConstraint(
                fields=['gateway', 'ref_id'],
                condition=models.Q(ref_id__gt=''),
                name='payment_ref_unique'),
            # پرداختِ بی‌صاحب یا دوصاحبه نباید ساخته شود.
            models.CheckConstraint(
                condition=(models.Q(order__isnull=False, custom_cake__isnull=True)
                           | models.Q(order__isnull=True, custom_cake__isnull=False)),
                name='payment_has_one_owner'),
        ]
        indexes = [
            models.Index(fields=['order', 'status'], name='payment_order_idx'),
            models.Index(fields=['custom_cake', 'status'], name='payment_cake_idx'),
        ]

    def __str__(self):
        owner = self.order or self.custom_cake
        return f'{owner.code if owner else "—"} — {self.get_gateway_display()} — {self.amount_rial}'

    @property
    def is_successful(self):
        return self.status == PaymentState.SUCCEEDED

    @property
    def is_refund(self):
        return self.kind == PaymentKind.REFUND

    @property
    def is_offline(self):
        """هر چیزی جز زرین‌پال دستی ثبت شده است."""
        return self.gateway != Gateway.ZARINPAL

    @property
    def is_sandbox(self):
        """پرداختی که بدون درگاه واقعی ثبت شده — پول واقعی نیست."""
        return self.gateway == Gateway.SANDBOX
