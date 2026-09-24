"""
کاربر، نشانی، علاقه‌مندی، کد یک‌بارمصرف، تلاش ورود.

منبع در تمپلیت:
    account/account.js      SEED.profile · SEED.addresses · SEED.favorites · TIERS
    auth/auth.js            فرم ثبت‌نام · پنل کد ۶ رقمی
    admin/auth-admin.js     MAX_TRIES · قفل حساب · تأیید دومرحله‌ای
"""

from django.conf import settings
from django.contrib.auth.hashers import check_password, make_password
from django.contrib.auth.models import AbstractBaseUser, BaseUserManager, PermissionsMixin
from django.db import models
from django.db.models import Q
from django.utils import timezone

from apps.common.models import SoftDeleteModel, TimeStampedModel
from apps.common.text import fix_letters, normalize_phone
from apps.common.validators import validate_phone, validate_postal_code


class Role(models.TextChoices):
    """
    سه نقش سایت.

    یک ستون روی User، نه یک جدول جدا. این بررسی در هر درخواستِ پنل اجرا
    می‌شود و نباید join لازم داشته باشد.

    گروه‌های جنگو هم کنارش می‌مانند، ولی برای دسترسی‌های ریز درون پنل
    ادمین؛ تصمیم «این آدم اصلاً به تابلوی آشپزخانه راه دارد یا نه» با
    همین ستون گرفته می‌شود.
    """

    CUSTOMER = 'customer', 'مشتری'
    KITCHEN = 'kitchen', 'ادمین قنادی'
    MANAGER = 'manager', 'مدیر'


class UserQuerySet(models.QuerySet):
    def customers(self):
        return self.filter(role=Role.CUSTOMER)

    def staff_members(self):
        return self.filter(role__in=(Role.KITCHEN, Role.MANAGER))

    def active(self):
        return self.filter(is_active=True, anonymized_at__isnull=True)

    def birthday_on(self, month, day):
        """برای یادآوری تولد — به همین دلیل تولد سه ستون عددی است."""
        return self.filter(birth_month=month, birth_day=day)


class UserManager(BaseUserManager):
    """
    مدیر کاربر با شماره‌ی موبایل به‌جای نام کاربری.

    شماره پیش از ذخیره نرمال می‌شود تا «۰۹۱۲…» و «+98912…» و «912…» یک
    رکورد باشند، نه سه‌تا.
    """

    def get_queryset(self):
        return UserQuerySet(self.model, using=self._db)

    def customers(self):
        return self.get_queryset().customers()

    def staff_members(self):
        return self.get_queryset().staff_members()

    def _create(self, phone, password, **extra):
        if not phone:
            raise ValueError('شماره موبایل الزامی است.')
        phone = normalize_phone(phone)
        user = self.model(phone=phone, **extra)
        if password:
            user.set_password(password)
        else:
            # ثبت‌نام با کد پیامکی رمز ندارد. رمز غیرقابل‌استفاده یعنی
            # ورود با رمز ممکن نیست، ولی حساب معتبر است.
            user.set_unusable_password()
        user.full_clean(exclude=['password', 'last_login'])
        user.save(using=self._db)
        return user

    def create_user(self, phone, password=None, **extra):
        extra.setdefault('role', Role.CUSTOMER)
        extra.setdefault('is_staff', False)
        extra.setdefault('is_superuser', False)
        return self._create(phone, password, **extra)

    def create_superuser(self, phone, password=None, **extra):
        extra.setdefault('role', Role.MANAGER)
        extra['is_staff'] = True
        extra['is_superuser'] = True
        extra['is_phone_verified'] = True
        return self._create(phone, password, **extra)


class User(AbstractBaseUser, PermissionsMixin, TimeStampedModel):
    """
    کاربر سایت — مشتری و کارکنان در یک جدول.

    چرا یک جدول: کارکنان قنادی خودشان هم مشتری‌اند و برایشان سفارش ثبت
    می‌شود. دو جدول یعنی یک آدم دو حساب.
    """

    phone = models.CharField(
        'شماره موبایل', max_length=11, unique=True, validators=[validate_phone],
        help_text='با ۰۹ شروع می‌شود. همین شناسه‌ی ورود است.')

    # فرم ورود کارکنان «نام کاربری» می‌خواهد نه شماره. برای مشتری خالی
    # می‌ماند؛ به همین دلیل null=True است نه blank تنها — چند رشته‌ی خالی
    # قید یکتایی را می‌شکنند ولی چند NULL نه.
    username = models.CharField(
        'نام کاربری', max_length=40, null=True, blank=True, unique=True,
        help_text='فقط برای کارکنان.')

    first_name = models.CharField('نام', max_length=60, blank=True)
    last_name = models.CharField('نام خانوادگی', max_length=60, blank=True)
    email = models.EmailField('ایمیل', blank=True)

    # تولد سه ستون عددی است نه یک رشته‌ی «۱۳۷۵/۰۴/۲۲»؛ «تولدهای این هفته»
    # باید کوئری‌پذیر باشد. سال و ماه و روزِ شمسی ذخیره می‌شوند چون کاربر
    # در تمپلیت همان را انتخاب می‌کند.
    birth_year = models.SmallIntegerField('سال تولد', null=True, blank=True)
    birth_month = models.SmallIntegerField('ماه تولد', null=True, blank=True, db_index=True)
    birth_day = models.SmallIntegerField('روز تولد', null=True, blank=True, db_index=True)

    role = models.CharField(
        'نقش', max_length=12, choices=Role.choices, default=Role.CUSTOMER, db_index=True)

    is_active = models.BooleanField('فعال', default=True)
    is_staff = models.BooleanField(
        'دسترسی به پنل جنگو', default=False,
        help_text='این با «نقش» فرق دارد؛ فقط ورود به /admin/ را کنترل می‌کند.')
    is_phone_verified = models.BooleanField('شماره تأیید شده', default=False)

    sms_opt_in = models.BooleanField('اطلاع‌رسانی پیامکی', default=True)
    email_opt_in = models.BooleanField('خبرنامه', default=False)

    # شمارنده‌های باشگاه. به‌جای COUNT گرفتن در هر بازدید پروفایل، در
    # گذار سفارش به «تحویل شد» با F() بالا می‌روند.
    orders_count = models.IntegerField('تعداد سفارش', default=0)
    total_spent_rial = models.BigIntegerField('مجموع خرید (ریال)', default=0)
    last_order_at = models.DateTimeField('آخرین سفارش', null=True, blank=True)

    # تأیید دومرحله‌ای پنل کارکنان — auth-admin.html
    totp_secret = models.CharField('کلید دومرحله‌ای', max_length=64, blank=True)
    totp_enabled = models.BooleanField('دومرحله‌ای فعال', default=False)

    last_login_ip = models.GenericIPAddressField('آخرین IP', null=True, blank=True)

    # حذف حساب = ناشناس‌سازی، نه DELETE. سفارش‌ها سند مالی‌اند و باید
    # بمانند؛ فقط هویت پاک می‌شود.
    anonymized_at = models.DateTimeField('زمان ناشناس‌سازی', null=True, blank=True)

    objects = UserManager()

    USERNAME_FIELD = 'phone'
    REQUIRED_FIELDS = []

    class Meta:
        verbose_name = 'کاربر'
        verbose_name_plural = 'کاربران'
        ordering = ('-created_at',)
        indexes = [
            models.Index(fields=['role', 'is_active'], name='user_role_active_idx'),
        ]

    def __str__(self):
        return self.full_name or self.phone

    def save(self, *args, **kwargs):
        self.phone = normalize_phone(self.phone)
        self.first_name = fix_letters(self.first_name or '').strip()
        self.last_name = fix_letters(self.last_name or '').strip()
        self.username = (self.username or '').strip() or None
        super().save(*args, **kwargs)

    # ── نمایش ──────────────────────────────────────────────────────

    @property
    def full_name(self):
        return f'{self.first_name} {self.last_name}'.strip()

    def get_full_name(self):
        return self.full_name

    def get_short_name(self):
        return self.first_name or self.phone

    @property
    def initials(self):
        """حرف اول نام و نام خانوادگی — آواتار گوشه‌ی هدر."""
        letters = [part[0] for part in (self.first_name, self.last_name) if part]
        return ''.join(letters) or 'ر'

    # ── نقش ────────────────────────────────────────────────────────

    @property
    def is_customer(self):
        return self.role == Role.CUSTOMER

    @property
    def is_kitchen(self):
        return self.role == Role.KITCHEN

    @property
    def is_manager(self):
        return self.role == Role.MANAGER

    @property
    def is_staff_member(self):
        return self.role in (Role.KITCHEN, Role.MANAGER)

    @property
    def can_use_staff_panel(self):
        """
        اجازه‌ی ورود از صفحه‌ی کارکنان.

        سه راه، و هر سه لازم‌اند:

        * ``is_staff_member`` — نقش قنادی یا مدیر، راه معمول.
        * ``is_staff`` — دسترسی به پنل جنگو.
        * ``is_superuser`` — و این یکی جدا آمده چون جنگو
          ``is_staff`` را از ``is_superuser`` نتیجه نمی‌گیرد. اگر کسی
          سهواً تیک «دسترسی به پنل» سوپریوزر را بردارد، بدون این شرط
          از صفحه‌ی کارکنان هم بیرون می‌ماند — یعنی از همان جایی که
          باید بتواند اشتباه را درست کند.

        ``is_staff_member`` با این فرق دارد: آن یکی «نقش در کافه» را
        می‌گوید و در تابلوی آشپزخانه به کار می‌رود؛ این یکی فقط
        «حق ورود از این در» است.
        """
        return bool(self.is_staff_member or self.is_staff or self.is_superuser)

    # ── حذف حساب ───────────────────────────────────────────────────

    def has_open_orders(self):
        """سفارشی که هنوز تحویل یا لغو نشده — مانع ناشناس‌سازی."""
        from apps.orders.models import FulfillmentStatus
        return self.orders.exclude(fulfillment_status__in=(
            FulfillmentStatus.DELIVERED, FulfillmentStatus.CANCELED)).exists()

    def anonymize(self):
        """
        ناشناس‌سازی، نه DELETE — هم از پنل کاربری، هم از پنل مدیریت.

        سفارش‌ها سند مالی‌اند و می‌مانند؛ هویت پاک می‌شود. شماره می‌ماند
        چون شناسه‌ی یکتای حساب است و سفارش‌های قدیمی با آن پیگیری می‌شوند.

        یک جا نوشته شده تا دو مسیرِ حذف از هم جدا نیفتند: پیش‌تر نسخه‌ی
        پنل مدیریت نشانی‌ها و علاقه‌مندی‌ها را جا می‌گذاشت.
        """
        from django.db import transaction
        with transaction.atomic():
            self.first_name = 'کاربر'
            self.last_name = 'حذف‌شده'
            self.email = ''
            self.username = None
            self.is_active = False
            self.is_staff = False
            self.sms_opt_in = False
            self.email_opt_in = False
            self.totp_secret = ''
            self.totp_enabled = False
            self.anonymized_at = timezone.now()
            self.set_unusable_password()
            self.save()
            # حذف واقعی، نه نرم: نشانی داده‌ی شخصی است و سفارش نسخه‌ی
            # خودش را دارد.
            self.addresses.all().hard_delete()
            self.favorites.all().delete()

    # ── باشگاه رُزِت ────────────────────────────────────────────────

    @property
    def tier(self):
        """
        پله‌ی باشگاه بر اساس تعداد سفارش — TIERS در account.js.

        جدول جدا لازم ندارد؛ چهار عدد ثابت در تنظیمات کافی است.
        """
        current = settings.LOYALTY_TIERS[0]
        for row in settings.LOYALTY_TIERS:
            if self.orders_count >= row[0]:
                current = row
        return {'name': current[1], 'at': current[0], 'next_at': current[2]}

    @property
    def orders_to_next_tier(self):
        next_at = self.tier['next_at']
        return None if next_at is None else max(0, next_at - self.orders_count)


class Address(TimeStampedModel, SoftDeleteModel):
    """
    نشانی ذخیره‌شده‌ی مشتری — SEED.addresses در account.js.

    حذف نرم است چون سفارش‌های قدیمی از روی همین ساخته شده‌اند. البته خودِ
    سفارش نسخه‌ی اسنپ‌شات دارد، ولی «نشانی حذف‌شده» باید قابل بازیابی
    باشد وقتی مشتری اشتباهی پاکش می‌کند.
    """

    user = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.CASCADE,
        related_name='addresses', verbose_name='کاربر')

    title = models.CharField('عنوان', max_length=40, help_text='خانه · محل کار')

    # تحویل‌گیرنده می‌تواند خود مشتری نباشد — کیک تولد را برای کسی
    # می‌فرستند.
    receiver_name = models.CharField('تحویل‌گیرنده', max_length=80)
    receiver_phone = models.CharField(
        'شماره تحویل‌گیرنده', max_length=11, validators=[validate_phone])

    province = models.CharField('استان', max_length=40, default='خراسان رضوی')
    city = models.CharField('شهر', max_length=40, default='مشهد')
    district = models.CharField('محله', max_length=60, blank=True)
    line = models.CharField('نشانی', max_length=300)
    plaque = models.CharField('پلاک', max_length=12, blank=True)
    unit = models.CharField('واحد', max_length=12, blank=True)
    postal_code = models.CharField(
        'کد پستی', max_length=10, blank=True, validators=[validate_postal_code])

    is_default = models.BooleanField('پیش‌فرض', default=False)

    class Meta:
        verbose_name = 'نشانی'
        verbose_name_plural = 'نشانی‌ها'
        ordering = ('-is_default', '-created_at')
        constraints = [
            # هر کاربر فقط یک نشانی پیش‌فرض. این قید در دیتابیس است نه در
            # کد — دو درخواست همزمان می‌توانند هر دو از بررسی پایتونی رد
            # شوند.
            models.UniqueConstraint(
                fields=['user'], condition=Q(is_default=True, deleted_at__isnull=True),
                name='address_one_default_per_user'),
        ]

    def __str__(self):
        return f'{self.title} — {self.line[:40]}'

    def save(self, *args, **kwargs):
        self.receiver_phone = normalize_phone(self.receiver_phone)
        super().save(*args, **kwargs)

    @property
    def one_line(self):
        # شهر و محله فقط وقتی جلو می‌آیند که در خودِ نشانی نیامده باشند.
        # فرم پنل کاربری یک کادر «نشانی کامل» دارد و کاربر شهر را همان‌جا
        # می‌نویسد؛ بدون این بررسی «مشهد، مشهد، بلوار…» درمی‌آمد.
        line = self.line or ''
        parts = [part for part in (self.city, self.district) if part and part not in line]
        parts.append(line)
        if self.plaque:
            parts.append(f'پلاک {self.plaque}')
        if self.unit:
            parts.append(f'واحد {self.unit}')
        return '، '.join(part for part in parts if part)

    def to_snapshot(self):
        """
        شکلی که در ``Order.address_snapshot`` می‌نشیند.

        سفارش نباید به این رکورد ارجاع بدهد: اگر مشتری فردا نشانی را
        ویرایش کند، برگه‌ی سفارشِ دیروز نباید عوض شود.
        """
        return {
            'title': self.title,
            'receiver_name': self.receiver_name,
            'receiver_phone': self.receiver_phone,
            'province': self.province,
            'city': self.city,
            'district': self.district,
            'line': self.line,
            'plaque': self.plaque,
            'unit': self.unit,
            'postal_code': self.postal_code,
        }


class Favorite(models.Model):
    """دکمه‌ی قلب روی کارت محصول — SEED.favorites."""

    user = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.CASCADE,
        related_name='favorites', verbose_name='کاربر')
    product = models.ForeignKey(
        'catalog.Product', on_delete=models.CASCADE,
        related_name='favorited_by', verbose_name='محصول')
    created_at = models.DateTimeField('زمان', auto_now_add=True)

    class Meta:
        verbose_name = 'علاقه‌مندی'
        verbose_name_plural = 'علاقه‌مندی‌ها'
        ordering = ('-created_at',)
        constraints = [
            models.UniqueConstraint(fields=['user', 'product'], name='favorite_unique'),
        ]

    def __str__(self):
        return f'{self.user} ♥ {self.product}'


class OTPPurpose(models.TextChoices):
    LOGIN = 'login', 'ورود'
    SIGNUP = 'signup', 'ثبت‌نام'
    RESET = 'reset', 'بازیابی رمز'
    CHANGE_PHONE = 'change_phone', 'تغییر شماره'


class OTPCode(TimeStampedModel):
    """
    کد یک‌بارمصرف پیامکی — پنل ۶ خانه‌ای auth.js.

    خودِ کد ذخیره نمی‌شود، فقط هشش. دسترسی خواندنی به دیتابیس — یک بکاپ
    گمشده، یک لاگ، یک کوئری اشتباه — نباید یعنی توانایی ورود به حساب
    مردم.
    """

    phone = models.CharField('شماره موبایل', max_length=11, db_index=True)
    purpose = models.CharField(
        'کاربرد', max_length=16, choices=OTPPurpose.choices, default=OTPPurpose.LOGIN)

    code_hash = models.CharField('هش کد', max_length=128)

    expires_at = models.DateTimeField('انقضا', db_index=True)
    used_at = models.DateTimeField('زمان استفاده', null=True, blank=True)
    attempts = models.SmallIntegerField('تعداد تلاش', default=0)

    ip = models.GenericIPAddressField('IP', null=True, blank=True)

    class Meta:
        verbose_name = 'کد یک‌بارمصرف'
        verbose_name_plural = 'کدهای یک‌بارمصرف'
        ordering = ('-created_at',)
        indexes = [
            models.Index(fields=['phone', 'purpose', '-created_at'], name='otp_lookup_idx'),
        ]

    def __str__(self):
        return f'{self.phone} — {self.get_purpose_display()}'

    def set_code(self, raw_code):
        self.code_hash = make_password(raw_code)

    def check_code(self, raw_code):
        return check_password(str(raw_code), self.code_hash)

    @property
    def is_expired(self):
        return timezone.now() >= self.expires_at

    @property
    def is_usable(self):
        return (self.used_at is None
                and not self.is_expired
                and self.attempts < settings.OTP_MAX_ATTEMPTS)

    @property
    def seconds_left(self):
        return max(0, int((self.expires_at - timezone.now()).total_seconds()))


class LoginAttempt(models.Model):
    """
    لاگ ورود — هر تلاش، موفق یا ناموفق.

    فقط ثبت می‌کند؛ هیچ قفلی اعمال نمی‌شود. اگر روزی دیدید کسی دارد رمز
    می‌زند، همین جدول نشان می‌دهد از کدام IP و چند بار.
    """

    phone = models.CharField('شماره/نام کاربری', max_length=40, db_index=True)
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, blank=True,
        related_name='login_attempts', verbose_name='کاربر')

    ip = models.GenericIPAddressField('IP', null=True, blank=True, db_index=True)
    user_agent = models.CharField('مرورگر', max_length=300, blank=True)

    is_staff_panel = models.BooleanField('ورود کارکنان', default=False)
    succeeded = models.BooleanField('موفق', default=False)
    failure_reason = models.CharField('دلیل ناموفقی', max_length=40, blank=True)

    created_at = models.DateTimeField('زمان', auto_now_add=True, db_index=True)

    class Meta:
        verbose_name = 'تلاش ورود'
        verbose_name_plural = 'تلاش‌های ورود'
        ordering = ('-created_at',)
        indexes = [
            models.Index(fields=['phone', 'succeeded', '-created_at'],
                         name='login_attempt_idx'),
        ]

    def __str__(self):
        mark = '✓' if self.succeeded else '✗'
        return f'{mark} {self.phone}'
