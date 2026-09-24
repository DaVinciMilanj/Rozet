"""
پنل کیک اختصاصی.
"""

from django.contrib import admin, messages
from django.urls import NoReverseMatch, reverse
from django.utils import timezone
from django.utils.html import format_html

from apps.common.admin import RoleRestrictedAdmin, TomanAdminMixin, toman_column
from apps.common.money import format_toman
from apps.common.text import to_persian_digits

from .models import (CakeCoating, CakeFilling, CakeFlavor, CakeImageKind,
                     CakeSize, CakeTerm, CustomCakeImage, CustomCakeRequest,
                     RequestStatus)


# ─────────────────────────────────────────────────────────────────────
#  گزینه‌ها
# ─────────────────────────────────────────────────────────────────────

class CakeOptionAdmin(TomanAdminMixin, RoleRestrictedAdmin):
    list_display = ('label', 'price_delta', 'sort_order', 'is_active')
    list_editable = ('sort_order', 'is_active')
    search_fields = ('label',)
    list_filter = ('is_active',)

    price_delta = toman_column('price_delta_rial', 'اختلاف قیمت (تومان)')


@admin.register(CakeSize)
class CakeSizeAdmin(TomanAdminMixin, RoleRestrictedAdmin):
    """اندازه تنها گزینه‌ای است که قیمت پایه دارد، نه اختلاف قیمت."""

    list_display = ('label', 'serves', 'approx_weight', 'base_price',
                    'max_tiers', 'sort_order', 'is_active')
    list_editable = ('sort_order', 'is_active')
    search_fields = ('label', 'serves')
    list_filter = ('is_active',)
    fields = ('label', ('serves', 'approx_weight'), 'description',
              'base_price_rial', 'max_tiers', ('sort_order', 'is_active'))

    base_price = toman_column('base_price_rial', 'قیمت پایه (تومان)')


@admin.register(CakeFlavor)
class CakeFlavorAdmin(CakeOptionAdmin):
    pass


@admin.register(CakeFilling)
class CakeFillingAdmin(CakeOptionAdmin):
    pass


@admin.register(CakeCoating)
class CakeCoatingAdmin(CakeOptionAdmin):
    """
    یادآوری: این **طعم** روکش است، نه جنسش.

    جنس روکش را طرح تعیین می‌کند؛ بعضی طرح‌ها فقط با فوندانت اجرا
    می‌شوند و اگر مشتری بتواند جنس را انتخاب کند، انتخابش با طرح تضاد
    می‌سازد.
    """


@admin.register(CakeTerm)
class CakeTermAdmin(RoleRestrictedAdmin):
    list_display = ('title', 'version', 'sort_order', 'is_active')
    list_editable = ('sort_order', 'is_active')
    search_fields = ('title', 'text')
    list_filter = ('version', 'is_active')


# ─────────────────────────────────────────────────────────────────────
#  تصاویر
# ─────────────────────────────────────────────────────────────────────

class CustomCakeImageInline(admin.TabularInline):
    """
    تصاویر آپلودی مشتری.

    این‌ها زیر ``PRIVATE_MEDIA_ROOT`` هستند و URL مستقیم ندارند؛
    پیش‌نمایش از ویوی مجوزدار ``custom_cake:image`` می‌آید.
    """

    model = CustomCakeImage
    extra = 0
    fields = ('preview', 'image', 'kind', 'caption', 'sort_order')
    readonly_fields = ('preview',)

    @admin.display(description='پیش‌نمایش')
    def preview(self, obj):
        if not obj.pk or not obj.image:
            return '—'
        try:
            url = reverse('custom_cake:image', args=[obj.pk])
        except NoReverseMatch:
            return obj.image.name
        border = '#7A2E46' if obj.kind == CakeImageKind.PRINT else '#E3E4DF'
        return format_html(
            '<a href="{}" target="_blank"><img src="{}" style="width:70px;height:70px;'
            'object-fit:cover;border-radius:6px;border:2px solid {}"></a>',
            url, url, border)


# ─────────────────────────────────────────────────────────────────────
#  درخواست
# ─────────────────────────────────────────────────────────────────────

@admin.register(CustomCakeRequest)
class CustomCakeRequestAdmin(TomanAdminMixin, RoleRestrictedAdmin):
    manager_only = False          # ادمین قنادی باید ببیند تا برآورد بدهد

    list_display = ('code_fa', 'full_name', 'phone_fa', 'event_date', 'mode',
                    'size', 'status', 'estimate', 'quoted', 'deadline')
    list_filter = ('status', 'mode', 'event_date', 'size', 'occasion')
    search_fields = ('code', 'contact_name', 'contact_family', 'contact_phone',
                     'contact_phone_alt', 'design_note', 'message_on_cake')
    date_hierarchy = 'event_date'
    autocomplete_fields = ('user', 'order', 'size', 'flavor', 'filling',
                           'coating', 'occasion', 'reviewed_by')
    inlines = (CustomCakeImageInline,)
    save_on_top = True
    list_per_page = 30

    fieldsets = (
        ('درخواست', {'fields': ('code', 'status', ('user', 'order'))}),
        ('تماس', {
            'fields': (('contact_name', 'contact_family'),
                       ('contact_phone', 'contact_phone_alt'), 'address'),
            'description': 'فرم دو شماره می‌گیرد؛ شماره‌ی دوم برای روزی است '
                           'که گوشی اول در دسترس نیست.',
        }),
        ('طرح', {'fields': ('mode', ('size', 'flavor'), ('filling', 'coating'),
                            ('tiers', 'color_theme'), 'occasion',
                            'message_on_cake', 'design_note', 'allergy_note')}),
        ('زمان', {'fields': ('event_date', 'cancel_deadline')}),
        ('مبالغ', {
            'fields': (('estimate_min_rial', 'estimate_max_rial'),
                       ('quoted_price_rial', 'deposit_rial'), 'print_fee_rial'),
            'description': 'برآورد را ویزارد حساب کرده است. «قیمت اعلام‌شده» '
                           'همان عددی است که بعد از دیدن طرح به مشتری می‌گویید.',
        }),
        ('داخلی', {'fields': ('staff_note', 'reviewed_by',
                              ('terms_accepted_at', 'terms_version'),
                              'created_at', 'updated_at')}),
    )

    readonly_fields = ('code', 'estimate_min_rial', 'estimate_max_rial',
                       'terms_accepted_at', 'terms_version',
                       'created_at', 'updated_at')

    def get_queryset(self, request):
        return super().get_queryset(request).select_related(
            'size', 'flavor', 'filling', 'coating', 'occasion', 'user')

    @admin.display(description='کد', ordering='code')
    def code_fa(self, obj):
        return to_persian_digits(obj.code)

    @admin.display(description='نام')
    def full_name(self, obj):
        return obj.full_name

    @admin.display(description='تماس', ordering='contact_phone')
    def phone_fa(self, obj):
        text = to_persian_digits(obj.contact_phone)
        if obj.contact_phone_alt:
            return format_html('{}<br><small>{}</small>', text,
                               to_persian_digits(obj.contact_phone_alt))
        return text

    @admin.display(description='برآورد')
    def estimate(self, obj):
        if not obj.estimate_max_rial:
            return '—'
        return format_html('{} تا {}',
                           format_toman(obj.estimate_min_rial),
                           format_toman(obj.estimate_max_rial))

    quoted = toman_column('quoted_price_rial', 'قیمت اعلام‌شده')

    @admin.display(description='مهلت لغو')
    def deadline(self, obj):
        if not obj.cancel_deadline:
            return '—'
        past = timezone.now() > obj.cancel_deadline
        return format_html('<span style="color:{}">{}</span>',
                           '#9E9E9E' if past else '#3F6B57',
                           'گذشته' if past else 'باز')

    def get_readonly_fields(self, request, obj=None):
        fields = list(super().get_readonly_fields(request, obj))
        if not self._is_manager(request):
            # ادمین قنادی قیمت اعلام نمی‌کند و بیعانه را عوض نمی‌کند.
            fields += ['quoted_price_rial', 'deposit_rial', 'print_fee_rial', 'order']
        return tuple(dict.fromkeys(fields))

    def has_delete_permission(self, request, obj=None):
        return False

    @admin.action(description='علامت‌زدن به‌عنوان «در حال بررسی»')
    def action_reviewing(self, request, queryset):
        updated = queryset.filter(status=RequestStatus.SUBMITTED).update(
            status=RequestStatus.REVIEWING, reviewed_by=request.user)
        self.message_user(request, f'{updated} درخواست در حال بررسی شد.')

    @admin.action(description='رد درخواست')
    def action_reject(self, request, queryset):
        if not self._is_manager(request):
            self.message_user(request, 'رد درخواست فقط از دسترس مدیر است.',
                              level=messages.ERROR)
            return
        updated = queryset.exclude(status=RequestStatus.CONVERTED).update(
            status=RequestStatus.REJECTED)
        self.message_user(request, f'{updated} درخواست رد شد.')

    actions = ('action_reviewing', 'action_reject')


@admin.register(CustomCakeImage)
class CustomCakeImageAdmin(RoleRestrictedAdmin):
    """
    فهرست جدا، چون گاهی باید یک عکس را سریع پیدا کرد.

    ``kind`` عمداً در فیلترها اول است: فرق «عکس نمونه» و «عکسی که روی کیک
    چاپ می‌شود» باید همیشه جلوی چشم باشد.
    """

    manager_only = False

    list_display = ('request', 'kind', 'caption', 'uploaded_at')
    list_filter = ('kind', 'uploaded_at')
    search_fields = ('request__code', 'caption')
    raw_id_fields = ('request',)
    readonly_fields = ('content_type', 'size_bytes', 'uploaded_at')
    list_select_related = ('request',)
