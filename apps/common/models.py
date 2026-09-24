"""
مدل‌های پایه‌ی مشترک، و جدول نرخ‌ها.

بیشتر چیزهای این فایل abstract هستند و جدول نمی‌سازند. تنها استثنا
``Pricing`` است.
"""

from django.core.exceptions import ValidationError
from django.core.validators import MaxValueValidator, MinValueValidator
from django.db import IntegrityError, models, transaction
from django.utils import timezone


class TimeStampedModel(models.Model):
    """زمان ساخت و آخرین ویرایش."""

    created_at = models.DateTimeField('زمان ثبت', auto_now_add=True, db_index=True)
    updated_at = models.DateTimeField('آخرین ویرایش', auto_now=True)

    class Meta:
        abstract = True


class SortableModel(models.Model):
    """
    ترتیب دستی.

    هرجا مدیر باید بگوید چه چیزی اول بیاید — دسته‌ها، تصاویر، اندازه‌ها،
    گزینه‌های ویزارد.
    """

    sort_order = models.SmallIntegerField(
        'ترتیب', default=0, db_index=True,
        help_text='عدد کوچک‌تر بالاتر می‌آید.')

    class Meta:
        abstract = True
        ordering = ('sort_order', 'id')


class ActivatableQuerySet(models.QuerySet):
    def active(self):
        return self.filter(is_active=True)


class ActivatableModel(models.Model):
    """
    روشن و خاموش کردن به‌جای حذف.

    محصولی که فروخته شده حذف نمی‌شود، چون فاکتورها به آن ارجاع دارند.
    """

    is_active = models.BooleanField('فعال', default=True, db_index=True)

    objects = ActivatableQuerySet.as_manager()

    class Meta:
        abstract = True


class SoftDeleteQuerySet(models.QuerySet):
    def alive(self):
        return self.filter(deleted_at__isnull=True)

    def delete(self):
        return self.update(deleted_at=timezone.now())

    def hard_delete(self):
        return super().delete()


class SoftDeleteModel(models.Model):
    """
    حذف نرم.

    برای رکوردهایی که کاربر «حذف» می‌زند ولی سیستم باید نگهشان دارد —
    مثل نشانی‌ای که روی سفارش قدیمی نشسته است.
    """

    deleted_at = models.DateTimeField('زمان حذف', null=True, blank=True, db_index=True)

    objects = SoftDeleteQuerySet.as_manager()

    class Meta:
        abstract = True

    def delete(self, using=None, keep_parents=False):
        self.deleted_at = timezone.now()
        self.save(update_fields=['deleted_at'])

    def hard_delete(self, using=None, keep_parents=False):
        super().delete(using=using, keep_parents=keep_parents)


CODE_ATTEMPTS = 10


def save_with_unique_code(instance, generator, saver, *args, **kwargs):
    """
    کد یکتا می‌سازد و در صورت برخورد دوباره تلاش می‌کند.

    دو لایه دارد، و هر دو لازم‌اند:

    * بررسی قبل از ذخیره — مسیر سریع، جلوی بیشتر برخوردها را
      می‌گیرد.
    * گرفتن ``IntegrityError`` — چون بین بررسی و ذخیره یک فاصله هست
      و دو سفارش همزمان می‌توانند هر دو از بررسی رد شوند.

    تراکنش جداگانه لازم است: بدون آن، ``IntegrityError`` کل تراکنش
    بیرونی را مسموم می‌کند و تلاش دوم هم شکست می‌خورد.
    """
    model = type(instance)
    for attempt in range(CODE_ATTEMPTS):
        instance.code = generator()
        if model.objects.filter(code=instance.code).exists():
            continue
        try:
            with transaction.atomic():
                saver(*args, **kwargs)
            return
        except IntegrityError:
            if attempt == CODE_ATTEMPTS - 1:
                raise
    raise IntegrityError('ساخت کد یکتا ناموفق ماند.')


class Pricing(models.Model):
    """
    نرخ‌های قابل تغییر — تک‌رکوردی.

    فقط عددهایی اینجا هستند که **با تورم عوض می‌شوند**. مشخصات قنادی
    (نشانی، ساعت کار، اینستاگرام) و قواعد ساختاری (حداقل سه روز تا
    تحویل، سقف چهار تصویر، پله‌های باشگاه) ثابت‌اند و در ``settings.py``
    می‌مانند؛ آن‌ها سالی یک‌بار هم عوض نمی‌شوند.

    چرا جدول و نه ثابت: نرخ پیک و بیعانه در ایران سالی چند بار بالا
    می‌روند. اگر در کد باشند، هر تغییرِ نرخ یعنی ویرایش فایل و ریستارت
    سرور — کاری که مدیر قنادی نمی‌تواند خودش انجام دهد.

    چرا در ``common``: هم ``orders`` و هم ``custom_cake`` از آن می‌خوانند،
    و ``common`` تنها اپی است که هر دو از قبل به آن وابسته‌اند. مالکِ
    این عددها هیچ‌کدام از آن دو نیست.
    """

    courier_enabled = models.BooleanField(
        'ارسال با پیک فعال', default=False,
        help_text='تا وقتی خاموش است، در ثبت سفارش فقط تحویل حضوری دیده می‌شود.')
    delivery_fee_rial = models.BigIntegerField('هزینه ارسال (ریال)', default=650_000)
    free_delivery_over_rial = models.BigIntegerField(
        'ارسال رایگان از (ریال)', default=15_000_000)
    gift_wrap_rial = models.BigIntegerField('بسته هدیه (ریال)', default=850_000)

    custom_deposit_rial = models.BigIntegerField(
        'بیعانه کیک اختصاصی (ریال)', default=4_000_000)
    custom_print_fee_rial = models.BigIntegerField(
        'هزینه چاپ عکس خوراکی (ریال)', default=2_500_000)

    # نرخ مالیات باید با حسابدار تأیید شود، نه از روی حدس پر شود. صفر
    # ماندنش بهتر از عدد اشتباه است — نرخ غلط روی همه‌ی فاکتورها می‌نشیند.
    vat_enabled = models.BooleanField('محاسبه مالیات', default=False)
    vat_percent = models.DecimalField(
        'نرخ مالیات (٪)', max_digits=5, decimal_places=2, default=0,
        validators=[MinValueValidator(0), MaxValueValidator(100)])

    updated_at = models.DateTimeField('آخرین تغییر', auto_now=True)

    class Meta:
        verbose_name = 'نرخ‌ها'
        verbose_name_plural = 'نرخ‌ها'

    def __str__(self):
        return 'نرخ‌ها'

    def clean(self):
        # رکورد دوم یعنی نیمی از سایت با نرخ قدیمی کار می‌کند و کسی
        # متوجه نمی‌شود.
        if not self.pk and Pricing.objects.exists():
            raise ValidationError('فقط یک رکورد نرخ می‌تواند وجود داشته باشد.')

    def save(self, *args, **kwargs):
        self.full_clean()
        super().save(*args, **kwargs)

    @classmethod
    def load(cls):
        pricing, _ = cls.objects.get_or_create(pk=1)
        return pricing

    def delivery_fee_for(self, items_total_rial):
        """هزینه‌ی ارسال این سفارش — با در نظر گرفتن سقف ارسال رایگان."""
        if not self.courier_enabled:
            return 0
        if items_total_rial >= self.free_delivery_over_rial:
            return 0
        return self.delivery_fee_rial

    def vat_for(self, amount_rial):
        if not self.vat_enabled or not self.vat_percent:
            return 0
        return int(amount_rial * self.vat_percent / 100)
