"""
ویترین: دسته، مناسبت، ویژگی، مجموعه، محصول و گزینه‌هایش.

منبع در تمپلیت:
    index.html                     تراشه‌های ماکارون/تارت/مینی‌کیک/شیرینی‌خشک
    product-list/product-list.js   PRODUCTS · CATEGORIES · OCCASIONS · FEATURES
    product-details.js             gallery · pyramid · SIZES · FLAVORS · ADDONS
"""

from django.conf import settings
from django.core.exceptions import ValidationError
from django.core.validators import MaxValueValidator, MinValueValidator
from django.db import models
from django.db.models import Avg, Count, Q
from django.urls import reverse
from django.utils.text import slugify

from apps.common.fields import ImageField
from apps.common.models import ActivatableModel, SortableModel, TimeStampedModel
from apps.common.text import fix_letters, normalize
from apps.common import upload


class Category(SortableModel, ActivatableModel):
    """
    دسته‌بندی محصول.

    ``parent`` دلخواه نیست: صفحه‌ی اصلی زیر «شیرینی» تراشه‌های
    ماکارون/تارت/مینی‌کیک/شیرینی‌خشک دارد که روی ``data-category`` کارت‌ها
    فیلتر می‌کنند. بدون سلسله‌مراتب، آن بخش از صفحه‌ی اصلی اصلاً کار
    نمی‌کند.
    """

    slug = models.SlugField('نشانی', max_length=60, unique=True, allow_unicode=True)
    name = models.CharField('نام', max_length=60)
    name_en = models.CharField('نام لاتین', max_length=60, blank=True)

    parent = models.ForeignKey(
        'self', on_delete=models.CASCADE, null=True, blank=True,
        related_name='children', verbose_name='دسته‌ی مادر')

    description = models.TextField('توضیح', blank=True)
    image = ImageField('تصویر', upload_to=upload.category_image, blank=True,
                       max_dimension=1600)

    show_in_megamenu = models.BooleanField('نمایش در مگامنو', default=True)
    show_on_home = models.BooleanField('نمایش در صفحه‌ی اصلی', default=False)

    class Meta:
        verbose_name = 'دسته'
        verbose_name_plural = 'دسته‌ها'
        ordering = ('sort_order', 'name')
        indexes = [
            models.Index(fields=['parent', 'sort_order'], name='category_tree_idx'),
        ]

    def __str__(self):
        return f'{self.parent.name} › {self.name}' if self.parent_id else self.name

    def save(self, *args, **kwargs):
        self.name = fix_letters(self.name).strip()
        if not self.slug:
            self.slug = slugify(self.name_en or self.name, allow_unicode=True)
        super().save(*args, **kwargs)

    def get_absolute_url(self):
        return f"{reverse('catalog:product_list')}?cat={self.slug}"

    @property
    def is_root(self):
        return self.parent_id is None


class Occasion(SortableModel, ActivatableModel):
    """
    مناسبت — OCCASIONS در product-list.js.

    تولد · عروسی · هدیه · مهمانی · هر روز. در ویزارد کیک اختصاصی هم همین
    فهرست استفاده می‌شود، پس جدول مشترک است نه دو تا.
    """

    slug = models.SlugField('نشانی', max_length=50, unique=True, allow_unicode=True)
    name = models.CharField('نام', max_length=50)
    icon = models.CharField('آیکن', max_length=100, blank=True)

    class Meta:
        verbose_name = 'مناسبت'
        verbose_name_plural = 'مناسبت‌ها'
        ordering = ('sort_order', 'name')

    def __str__(self):
        return self.name


class ProductFeature(SortableModel, ActivatableModel):
    """
    ویژگی فیلترشونده — FEATURES در product-list.js.

    آماده امروز · بدون آجیل · بدون تخم‌مرغ · جعبه کادویی.

    اینها با ``Product.allergens`` فرق دارند: ویژگی چیزی است که مشتری با
    آن فیلتر می‌کند، حساسیت متنی است که می‌خواند.
    """

    slug = models.SlugField('نشانی', max_length=50, unique=True, allow_unicode=True)
    name = models.CharField('نام', max_length=50)
    icon = models.CharField('آیکن', max_length=40, blank=True)

    class Meta:
        verbose_name = 'ویژگی'
        verbose_name_plural = 'ویژگی‌ها'
        ordering = ('sort_order', 'name')

    def __str__(self):
        return self.name


class Badge(models.TextChoices):
    NONE = '', '—'
    BESTSELLER = 'bestseller', 'پرفروش'
    NEW = 'new', 'تازه'
    SEASONAL = 'seasonal', 'فصلی'
    LIMITED = 'limited', 'محدود'


class ProductQuerySet(models.QuerySet):
    def live(self):
        return self.filter(is_active=True)

    def in_stock(self):
        return self.filter(is_active=True, in_stock=True)

    def search(self, term):
        """
        جست‌وجوی فارسی.

        عبارت کاربر با همان تابعی نرمال می‌شود که ``search_norm`` با آن
        ساخته شده. نرمال‌کردن فقط یک طرف، هیچ فایده‌ای ندارد.
        """
        term = normalize(term)
        if not term:
            return self
        return self.filter(search_norm__contains=term)

    def with_cover(self):
        return self.prefetch_related('images')


class Product(TimeStampedModel, ActivatableModel):
    """
    محصول ویترین.

    قیمت به ریال ذخیره می‌شود و در نمایش تومان می‌شود. جزئیات در
    ``apps/common/money.py``.
    """

    slug = models.SlugField(
        'نشانی', max_length=80, unique=True, allow_unicode=True, blank=True,
        help_text='خالی بگذارید تا از نام لاتین ساخته شود.')
    name = models.CharField('نام', max_length=100)
    name_en = models.CharField('نام لاتین', max_length=100, blank=True)

    category = models.ForeignKey(
        Category, on_delete=models.PROTECT,
        related_name='products', verbose_name='دسته')
    occasions = models.ManyToManyField(
        Occasion, blank=True, related_name='products', verbose_name='مناسبت‌ها')
    features = models.ManyToManyField(
        ProductFeature, blank=True, related_name='products', verbose_name='ویژگی‌ها')

    price_rial = models.BigIntegerField(
        'قیمت (ریال)', validators=[MinValueValidator(0)],
        help_text='به ریال وارد کنید. در سایت تومان نمایش داده می‌شود.')
    compare_at_price_rial = models.BigIntegerField(
        'قیمت پیش از تخفیف (ریال)', null=True, blank=True,
        validators=[MinValueValidator(0)])

    short_description = models.CharField(
        'توضیح کوتاه', max_length=200, blank=True,
        help_text='بخش‌ها را با « · » جدا کنید؛ کارت محصول همان‌جا می‌شکندش.')
    description = models.TextField('توضیح', blank=True)

    serves = models.CharField(
        'اندازه', max_length=60, blank=True,
        help_text='۶ تا ۸ نفر · پک ۶ عددی · حدود ۱٫۵ کیلو')

    badge = models.CharField('نشان', max_length=12, choices=Badge.choices, blank=True)

    # سه بند آکاردئون صفحه‌ی جزئیات
    ingredients = models.TextField('مواد اولیه', blank=True)
    allergens = models.TextField('هشدار حساسیت', blank=True)
    keeping = models.TextField('نگهداری', blank=True)

    # از روی نظرهای تأییدشده حساب می‌شوند، نه دستی. ذخیره‌شان به‌جای
    # محاسبه در هر بار، برای این است که فهرست محصولات با هشت کارت
    # نباید هشت کوئری میانگین بزند.
    rating = models.DecimalField(
        'امتیاز', max_digits=3, decimal_places=2, default=0, editable=False)
    reviews_count = models.IntegerField('تعداد نظر', default=0, editable=False)

    prep_days = models.SmallIntegerField(
        'روز آماده‌سازی', default=0,
        help_text='حداقل فاصله تا تحویل. صفر یعنی همان روز.')

    in_stock = models.BooleanField(
        'موجود', default=True,
        help_text='ادمین قنادی فقط همین را می‌تواند تغییر دهد.')

    sales_count = models.IntegerField('تعداد فروش', default=0, db_index=True)

    # شکل نرمال‌شده‌ی نام و توضیح، برای جست‌وجوی فارسی. در save() پر
    # می‌شود. روی پستگرس این ستون GENERATED می‌شود و با pg_trgm ایندکس.
    search_norm = models.TextField('نمایه‌ی جست‌وجو', blank=True, editable=False)

    meta_title = models.CharField('عنوان سئو', max_length=120, blank=True)
    meta_description = models.CharField('توضیح سئو', max_length=200, blank=True)

    objects = ProductQuerySet.as_manager()

    class Meta:
        verbose_name = 'محصول'
        verbose_name_plural = 'محصولات'
        ordering = ('-created_at',)
        indexes = [
            models.Index(fields=['category', 'is_active'], name='product_cat_idx'),
            models.Index(fields=['is_active', '-sales_count'], name='product_best_idx'),
            models.Index(fields=['is_active', 'price_rial'], name='product_price_idx'),
            # ایندکس جزئی: فقط ردیف‌های زنده. کوئری فهرست همیشه این شرط را
            # دارد و ایندکس کوچک‌تر یعنی جست‌وجوی سریع‌تر.
            models.Index(fields=['-created_at'], condition=Q(is_active=True),
                         name='product_live_new_idx'),
        ]
        constraints = [
            models.CheckConstraint(
                condition=Q(price_rial__gte=0), name='product_price_non_negative'),
        ]

    def __str__(self):
        return self.name

    def save(self, *args, **kwargs):
        self.name = fix_letters(self.name).strip()
        if not self.slug:
            base = slugify(self.name_en or self.name, allow_unicode=True) or 'product'
            slug, index = base, 2
            while Product.objects.filter(slug=slug).exclude(pk=self.pk).exists():
                slug = f'{base}-{index}'
                index += 1
            self.slug = slug
        self.search_norm = normalize(
            ' '.join([self.name, self.name_en, self.short_description, self.serves]))
        super().save(*args, **kwargs)

    def clean(self):
        # «قیمت پیش از تخفیف» که از قیمت فعلی کمتر باشد، روی کارت محصول
        # تخفیفِ منفی نشان می‌دهد.
        if (self.compare_at_price_rial
                and self.compare_at_price_rial <= self.price_rial):
            raise ValidationError({'compare_at_price_rial':
                                   'باید از قیمت فعلی بیشتر باشد.'})

    def get_absolute_url(self):
        return reverse('catalog:product_detail', kwargs={'slug': self.slug})

    # ── نمایش ──────────────────────────────────────────────────────

    @property
    def cover(self):
        """
        تصویر کاور.

        از ``images.all()`` می‌خواند نه یک کوئری جدا، تا وقتی ویو
        ``prefetch_related('images')`` زده، این N+1 نسازد.
        """
        images = list(self.images.all())
        for image in images:
            if image.is_cover:
                return image
        return images[0] if images else None

    @property
    def has_discount(self):
        return bool(self.compare_at_price_rial
                    and self.compare_at_price_rial > self.price_rial)

    @property
    def discount_percent(self):
        if not self.has_discount:
            return 0
        gap = self.compare_at_price_rial - self.price_rial
        return int(round(gap * 100 / self.compare_at_price_rial))

    @property
    def is_available(self):
        return self.is_active and self.in_stock

    def refresh_rating(self):
        """
        میانگین و تعداد را از روی نظرهای **تأییدشده** دوباره می‌سازد.

        با ``update()`` نوشته می‌شود نه ``save()`` — چون ``save()`` نمایه‌ی
        جست‌وجو را هم بازمی‌سازد و اینجا لازم نیست.
        """
        stats = self.reviews.filter(is_approved=True).aggregate(
            average=Avg('rating'), total=Count('id'))
        rating = round(stats['average'] or 0, 2)
        count = stats['total']
        type(self).objects.filter(pk=self.pk).update(
            rating=rating, reviews_count=count)
        self.rating, self.reviews_count = rating, count


class ProductImage(SortableModel):
    """گالری محصول — سه تصویر با بندانگشتی و بزرگ‌نمایی."""

    product = models.ForeignKey(
        Product, on_delete=models.CASCADE, related_name='images', verbose_name='محصول')
    # ۱۶۰۰ پیکسل: برای بزرگ‌نمایی صفحه‌ی جزئیات کافی، و چند برابر سبک‌تر از
    # عکس خامِ دوربین.
    image = ImageField('تصویر', upload_to=upload.product_image, max_dimension=1600)
    alt = models.CharField(
        'متن جایگزین', max_length=140, blank=True,
        help_text='برای صفحه‌خوان و وقتی تصویر بالا نمی‌آید.')
    is_cover = models.BooleanField('تصویر اصلی', default=False)

    class Meta:
        verbose_name = 'تصویر محصول'
        verbose_name_plural = 'تصاویر محصول'
        ordering = ('-is_cover', 'sort_order', 'id')
        constraints = [
            # هر محصول فقط یک کاور — قید جزئی، در دیتابیس.
            models.UniqueConstraint(
                fields=['product'], condition=Q(is_cover=True),
                name='product_one_cover'),
        ]

    def __str__(self):
        return f'{self.product.name} — {self.sort_order}'


class ProductOption(SortableModel, ActivatableModel):
    """
    پایه‌ی مشترک اندازه و طعم و افزودنی.

    ``price_delta_rial`` اختلاف ریالی است، نه ضریب. تمپلیت برای اندازه
    ضریب داشت (``mult: 1.42``) ولی ضریب یعنی قیمت نهایی در هر صفحه با یک
    گِردکردن متفاوت درمی‌آید و مبلغ کارت با مبلغ درگاه یکی نمی‌شود.
    """

    label = models.CharField('عنوان', max_length=60)
    price_delta_rial = models.BigIntegerField('اختلاف قیمت (ریال)', default=0)
    is_default = models.BooleanField('پیش‌فرض', default=False)

    class Meta:
        abstract = True
        ordering = ('sort_order', 'id')

    def __str__(self):
        return self.label


class ProductSize(ProductOption):
    """SIZES در product-details.js."""

    product = models.ForeignKey(
        Product, on_delete=models.CASCADE, related_name='sizes', verbose_name='محصول')
    serves = models.CharField('تعداد نفرات', max_length=60, blank=True,
                              help_text='۸ تا ۱۰ نفر — حدود ۲ کیلو')

    class Meta(ProductOption.Meta):
        verbose_name = 'اندازه'
        verbose_name_plural = 'اندازه‌ها'
        constraints = [
            models.UniqueConstraint(
                fields=['product'], condition=Q(is_default=True),
                name='product_one_default_size'),
        ]


class ProductFlavor(ProductOption):
    """FLAVORS در product-details.js."""

    product = models.ForeignKey(
        Product, on_delete=models.CASCADE, related_name='flavors', verbose_name='محصول')

    class Meta(ProductOption.Meta):
        verbose_name = 'طعم'
        verbose_name_plural = 'طعم‌ها'
        constraints = [
            models.UniqueConstraint(
                fields=['product'], condition=Q(is_default=True),
                name='product_one_default_flavor'),
        ]


class ProductAddon(ProductOption):
    """ADDONS در product-details.js — شمع، کارت دست‌نویس، جعبه‌ی ویژه."""

    product = models.ForeignKey(
        Product, on_delete=models.CASCADE, related_name='addons', verbose_name='محصول')
    description = models.CharField('توضیح', max_length=120, blank=True)

    class Meta(ProductOption.Meta):
        verbose_name = 'افزودنی'
        verbose_name_plural = 'افزودنی‌ها'


class ProductFlavorNote(SortableModel):
    """
    نت هرم طعم — ``pyramid: [{n: 'گلاب کاشان', v: 90}]``.

    چرا مدل و نه JSONField: ``JSONField(default=list, blank=True)`` وقتی
    فرم ادمین خالی بماند ``None`` می‌فرستد و ``default`` اجرا نمی‌شود —
    همان ``NOT NULL constraint failed`` معروف. به‌علاوه در پنل، inline
    پرکردن از تایپ‌کردن JSON با دست خیلی کم‌خطاتر است.
    """

    product = models.ForeignKey(
        Product, on_delete=models.CASCADE,
        related_name='flavor_notes', verbose_name='محصول')
    label = models.CharField('نت', max_length=60, help_text='گلاب کاشان')
    weight = models.SmallIntegerField(
        'شدت', default=50, validators=[MinValueValidator(0), MaxValueValidator(100)],
        help_text='عددی بین ۰ تا ۱۰۰ — عرض نوار در صفحه‌ی محصول.')

    class Meta:
        verbose_name = 'نت طعم'
        verbose_name_plural = 'هرم طعم'
        ordering = ('sort_order', '-weight')

    def __str__(self):
        return f'{self.label} ({self.weight}٪)'


class GalleryImage(SortableModel, ActivatableModel):
    """نوار «رُزِت در اینستاگرام» و گالری صفحه‌ی درباره‌ما."""

    image = ImageField('تصویر', upload_to=upload.gallery_image, max_dimension=1600)
    alt = models.CharField('متن جایگزین', max_length=140, blank=True)
    caption = models.CharField('عنوان', max_length=120, blank=True)
    link = models.URLField('لینک', blank=True)

    class Meta:
        verbose_name = 'تصویر گالری'
        verbose_name_plural = 'گالری'
        ordering = ('sort_order', '-id')

    def __str__(self):
        return self.caption or f'تصویر {self.pk}'


class Review(models.Model):
    """
    نظر و امتیاز مشتری روی یک محصول.

    همان چیزی که صفحه‌ی جزئیات نشان می‌دهد و نه بیشتر: یک امتیاز، یک
    متن، یک تأیید. نه رأی «مفید بود»، نه پاسخ قنادی، نه عکس.

    ``text`` می‌تواند خالی باشد — در تمپلیت هم می‌شود فقط ستاره داد.
    """

    product = models.ForeignKey(
        Product, on_delete=models.CASCADE,
        related_name='reviews', verbose_name='محصول')
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.CASCADE,
        related_name='reviews', verbose_name='کاربر')

    rating = models.SmallIntegerField(
        'امتیاز', validators=[MinValueValidator(1), MaxValueValidator(5)])
    text = models.TextField('متن نظر', max_length=1000, blank=True)

    # پیش‌فرض خاموش. بدون آن، اولین ربات اسپم هر چه بخواهد روی صفحه‌ی
    # محصول می‌نویسد و تا وقتی کسی ببیند، روی گوگل هم نشسته است.
    is_approved = models.BooleanField(
        'تأیید شده', default=False,
        help_text='تا تأیید نشود در سایت دیده نمی‌شود.')

    created_at = models.DateTimeField('زمان', auto_now_add=True)

    class Meta:
        verbose_name = 'نظر'
        verbose_name_plural = 'نظرها'
        ordering = ('-created_at',)
        constraints = [
            # هر کاربر روی هر محصول یک نظر. بدون این، یک نفر با ده نظر
            # پنج‌ستاره میانگین را جابه‌جا می‌کند.
            models.UniqueConstraint(fields=['product', 'user'],
                                    name='review_one_per_user'),
        ]
        indexes = [
            # تنها کوئری پرتکرار: نظرهای تأییدشده‌ی یک محصول، تازه‌ترین
            # اول. هر سه ستون در یک ایندکس، پس نه جست‌وجوی جدول لازم است
            # نه مرتب‌سازی جداگانه.
            models.Index(fields=['product', 'is_approved', '-created_at'],
                         name='review_public_idx'),
        ]

    def __str__(self):
        return f'{self.product.name} — {self.rating}/5'

    @property
    def display_name(self):
        """«مریم ک.» — نام کوچک و حرف اول فامیل، مثل تمپلیت."""
        first = self.user.first_name or 'مشتری'
        last = self.user.last_name
        return f'{first} {last[0]}.' if last else first

    def save(self, *args, **kwargs):
        super().save(*args, **kwargs)
        self.product.refresh_rating()

    def delete(self, *args, **kwargs):
        product = self.product
        super().delete(*args, **kwargs)
        product.refresh_rating()
