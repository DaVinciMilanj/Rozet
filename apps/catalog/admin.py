"""
پنل ویترین.

ادمین قنادی اینجا فقط یک کار دارد: روشن و خاموش کردن «موجود». قیمت و
محصول و دسته دست مدیر است.
"""

from django.contrib import admin
from django.db.models import Count
from django.utils.html import format_html

from apps.common.admin import RoleRestrictedAdmin, TomanAdminMixin, toman_column
from apps.common.text import to_persian_digits

from .models import (Category, GalleryImage, Occasion, Product, ProductAddon,
                     ProductFeature, ProductFlavor, ProductFlavorNote,
                     ProductImage, ProductSize, Review)


def thumb(image_field, size=52):
    if not image_field:
        return '—'
    return format_html(
        '<img src="{}" style="width:{}px;height:{}px;object-fit:cover;'
        'border-radius:6px" loading="lazy">',
        image_field.url, size, size)


# ─────────────────────────────────────────────────────────────────────
#  دسته و برچسب
# ─────────────────────────────────────────────────────────────────────

@admin.register(Category)
class CategoryAdmin(RoleRestrictedAdmin):
    list_display = ('name', 'parent', 'product_count', 'show_in_megamenu',
                    'show_on_home', 'sort_order', 'is_active')
    list_editable = ('sort_order', 'is_active', 'show_in_megamenu', 'show_on_home')
    list_filter = ('is_active', 'show_in_megamenu', 'parent')
    search_fields = ('name', 'name_en', 'slug')
    autocomplete_fields = ('parent',)
    list_select_related = ('parent',)
    fields = (('name', 'name_en'), 'slug', 'parent', 'description', 'image',
              ('show_in_megamenu', 'show_on_home'), ('sort_order', 'is_active'))

    def get_queryset(self, request):
        return super().get_queryset(request).annotate(_products=Count('products'))

    @admin.display(description='محصول', ordering='_products')
    def product_count(self, obj):
        return to_persian_digits(obj._products)


@admin.register(Occasion)
class OccasionAdmin(RoleRestrictedAdmin):
    list_display = ('name', 'slug', 'sort_order', 'is_active')
    list_editable = ('sort_order', 'is_active')
    search_fields = ('name', 'slug')


@admin.register(ProductFeature)
class ProductFeatureAdmin(RoleRestrictedAdmin):
    list_display = ('name', 'slug', 'sort_order', 'is_active')
    list_editable = ('sort_order', 'is_active')
    search_fields = ('name', 'slug')


# ─────────────────────────────────────────────────────────────────────
#  اینلاین‌های محصول
# ─────────────────────────────────────────────────────────────────────

class ProductImageInline(admin.TabularInline):
    model = ProductImage
    extra = 1
    fields = ('preview', 'image', 'alt', 'is_cover', 'sort_order')
    readonly_fields = ('preview',)

    @admin.display(description='پیش‌نمایش')
    def preview(self, obj):
        return thumb(obj.image)


class ProductSizeInline(TomanAdminMixin, admin.TabularInline):
    model = ProductSize
    extra = 0
    fields = ('label', 'serves', 'price_delta_rial',
              'is_default', 'sort_order', 'is_active')


class ProductFlavorInline(TomanAdminMixin, admin.TabularInline):
    model = ProductFlavor
    extra = 0
    fields = ('label', 'price_delta_rial', 'is_default', 'sort_order', 'is_active')


class ProductAddonInline(TomanAdminMixin, admin.TabularInline):
    model = ProductAddon
    extra = 0
    fields = ('label', 'description', 'price_delta_rial', 'sort_order', 'is_active')


class ProductFlavorNoteInline(admin.TabularInline):
    """
    هرم طعم.

    همین اینلاین دلیل مدل‌بودنِ هرم طعم است: پرکردن سه فیلد در یک ردیف،
    در برابر تایپ‌کردن ``[{"n": "...", "v": 90}]`` با دست در یک تکست‌اریا.
    """

    model = ProductFlavorNote
    extra = 0
    fields = ('label', 'weight', 'sort_order')


# ─────────────────────────────────────────────────────────────────────
#  محصول
# ─────────────────────────────────────────────────────────────────────

@admin.register(Product)
class ProductAdmin(TomanAdminMixin, RoleRestrictedAdmin):
    manager_only = False          # ادمین قنادی هم می‌بیند
    kitchen_readonly = False      # ...و فقط «موجود» را عوض می‌کند

    list_display = ('cover_thumb', 'name', 'category', 'price', 'badge',
                    'in_stock', 'is_active', 'sales')
    list_display_links = ('cover_thumb', 'name')
    list_editable = ('in_stock',)
    list_filter = ('is_active', 'in_stock', 'category', 'badge',
                   'occasions', 'features')
    search_fields = ('name', 'name_en', 'slug', 'short_description')
    autocomplete_fields = ('category',)
    filter_horizontal = ('occasions', 'features')
    list_select_related = ('category',)
    list_per_page = 30
    save_on_top = True
    readonly_fields = ('rating', 'reviews_count')

    inlines = (ProductImageInline, ProductSizeInline, ProductFlavorInline,
               ProductAddonInline, ProductFlavorNoteInline)

    fieldsets = (
        ('شناسه', {'fields': (('name', 'name_en'), 'slug', 'category', 'badge')}),
        ('قیمت', {
            'fields': (('price_rial', 'compare_at_price_rial'),),
            'description': 'مبلغ‌ها را به <b>تومان</b> وارد کنید؛ ذخیره به ریال است.',
        }),
        ('معرفی', {'fields': ('short_description', 'description', 'serves')}),
        ('دسته‌بندی', {'fields': ('occasions', 'features')}),
        ('جزئیات', {'fields': ('ingredients', 'allergens', 'keeping')}),
        ('موجودی', {'fields': (('in_stock', 'is_active'), 'prep_days')}),
        ('آمار', {
            'classes': ('collapse',),
            'fields': (('rating', 'reviews_count'), 'sales_count'),
            'description': 'امتیاز و تعداد نظر از روی نظرهای تأییدشده '
                           'حساب می‌شوند و دستی قابل تغییر نیستند.',
        }),
        ('سئو', {'classes': ('collapse',), 'fields': ('meta_title', 'meta_description')}),
    )

    def get_queryset(self, request):
        # بدون این، هر ردیف فهرست یک کوئری برای تصویر کاور می‌زند.
        return super().get_queryset(request).prefetch_related('images')

    @admin.display(description='تصویر')
    def cover_thumb(self, obj):
        cover = obj.cover
        return thumb(cover.image) if cover else '—'

    price = toman_column('price_rial', 'قیمت (تومان)')

    @admin.display(description='فروش', ordering='sales_count')
    def sales(self, obj):
        return to_persian_digits(obj.sales_count)

    # ── دسترسی ادمین قنادی ─────────────────────────────────────────

    def get_readonly_fields(self, request, obj=None):
        if self._is_manager(request):
            return super().get_readonly_fields(request, obj)
        # ادمین قنادی: همه‌چیز قفل جز موجودی.
        return [field.name for field in self.model._meta.fields
                if field.name != 'in_stock']

    def get_inlines(self, request, obj):
        return () if not self._is_manager(request) else self.inlines

    def has_add_permission(self, request):
        return self._is_manager(request)

    def has_delete_permission(self, request, obj=None):
        # محصول فروخته‌شده حذف نمی‌شود؛ «فعال» را خاموش کنید. حذف یعنی
        # اقلام سفارش‌های قدیمی ارجاعشان را از دست می‌دهند.
        return False

    @admin.action(description='علامت‌زدن به‌عنوان ناموجود')
    def mark_out_of_stock(self, request, queryset):
        updated = queryset.update(in_stock=False)
        self.message_user(request, f'{updated} محصول ناموجود شد.')

    @admin.action(description='علامت‌زدن به‌عنوان موجود')
    def mark_in_stock(self, request, queryset):
        updated = queryset.update(in_stock=True)
        self.message_user(request, f'{updated} محصول موجود شد.')

    actions = ('mark_in_stock', 'mark_out_of_stock')


@admin.register(GalleryImage)
class GalleryImageAdmin(RoleRestrictedAdmin):
    list_display = ('preview', 'caption', 'sort_order', 'is_active')
    list_display_links = ('preview', 'caption')
    list_editable = ('sort_order', 'is_active')
    list_filter = ('is_active',)

    @admin.display(description='تصویر')
    def preview(self, obj):
        return thumb(obj.image, 64)


@admin.register(Review)
class ReviewAdmin(RoleRestrictedAdmin):
    """
    نظرها — کار روزانه‌اش یک نگاه و یک تیک است.

    فهرست پیش‌فرض روی «منتظر تأیید» باز می‌شود، چون سؤال هر روزِ مدیر
    همین است، نه مرور دوباره‌ی نظرهای تأییدشده.
    """

    list_display = ('created_at', 'product', 'user', 'stars', 'excerpt', 'is_approved')
    list_editable = ('is_approved',)
    list_filter = ('is_approved', 'rating', 'created_at')
    search_fields = ('text', 'product__name', 'user__phone',
                     'user__first_name', 'user__last_name')
    autocomplete_fields = ('product', 'user')
    list_select_related = ('product', 'user')
    date_hierarchy = 'created_at'
    readonly_fields = ('created_at',)
    fields = ('product', 'user', 'rating', 'text', 'is_approved', 'created_at')

    def changelist_view(self, request, extra_context=None):
        if 'is_approved__exact' not in request.GET:
            params = request.GET.copy()
            params['is_approved__exact'] = '0'
            request.GET = params
            request.META['QUERY_STRING'] = params.urlencode()
        return super().changelist_view(request, extra_context)

    @admin.display(description='امتیاز', ordering='rating')
    def stars(self, obj):
        return '★' * obj.rating + '☆' * (5 - obj.rating)

    @admin.display(description='متن')
    def excerpt(self, obj):
        if not obj.text:
            return '—'
        return obj.text[:60] + ('…' if len(obj.text) > 60 else '')

    def _set_approved(self, queryset, approved):
        # update() متد save() را رد می‌کند، پس میانگین محصول‌های درگیر را
        # خودمان دوباره می‌سازیم.
        products = {review.product for review in queryset}
        count = queryset.update(is_approved=approved)
        for product in products:
            product.refresh_rating()
        return count

    @admin.action(description='تأیید و نمایش در سایت')
    def approve(self, request, queryset):
        self.message_user(request, f'{self._set_approved(queryset, True)} نظر تأیید شد.')

    @admin.action(description='برداشتن تأیید')
    def unapprove(self, request, queryset):
        self.message_user(request,
                          f'{self._set_approved(queryset, False)} نظر از سایت برداشته شد.')

    actions = ('approve', 'unapprove')
