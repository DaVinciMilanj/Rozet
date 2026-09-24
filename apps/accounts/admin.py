"""
پنل کاربران.

دسترسی به جدول کاربران حساس‌ترین بخش پنل است، چون از همین‌جا می‌شود
به کسی دسترسی داد. قاعده‌ها:

* **ادمین قنادی** این بخش را اصلاً نمی‌بیند (``manager_only``).
* **مدیر** مشتری‌ها و ادمین‌های قنادی را می‌سازد و ویرایش می‌کند، ولی
  نقش را حداکثر تا «ادمین قنادی» می‌تواند بدهد. مدیر دیگر و سوپریوزر
  برایش فقط‌خواندنی‌اند — حتی رمزشان را نمی‌تواند عوض کند. بدون این،
  هر مدیری می‌توانست یک حساب تازه بسازد و خودش را با آن بالا بکشد.
* **سوپریوزر** همه‌چیز.
* هیچ‌کس نقش، فعال‌بودن یا سوپریوزر بودنِ **خودش** را از اینجا عوض
  نمی‌کند؛ یک کلیک اشتباه یعنی قفل‌شدن بیرون از پنل.

کلید دومرحله‌ای (``totp_secret``) هیچ‌جا نمایش داده نمی‌شود. کسی که
آن را ببیند می‌تواند کد تولید کند.
"""

from django import forms
from django.contrib import admin, messages
from django.contrib.auth.admin import UserAdmin as BaseUserAdmin
from django.contrib.auth.forms import ReadOnlyPasswordHashField
from django.contrib.auth.password_validation import validate_password
from django.utils.html import format_html

from apps.common.admin import ReadOnlyAdmin, RoleRestrictedAdmin, RoleRestrictedMixin
from apps.common.money import format_toman
from apps.common.text import fix_digits, normalize_phone, to_persian_digits

from .models import Address, Favorite, LoginAttempt, OTPCode, Role, User

STAFF_ROLES = (Role.KITCHEN, Role.MANAGER)


def _is_superuser(request):
    return bool(request.user.is_superuser)


def can_edit_user(request, target):
    """
    آیا این کاربرِ پنل می‌تواند ``target`` را ویرایش کند؟

    ``target`` خالی یعنی فهرست یا فرم ساخت — آن‌ها را قاعده‌ی نقش
    (``RoleRestrictedMixin``) می‌سنجد.
    """
    if target is None or _is_superuser(request):
        return True
    if target.pk == request.user.pk:
        return True
    return not (target.is_superuser or target.is_manager)


# ─────────────────────────────────────────────────────────────────────
#  فرم‌ها
# ─────────────────────────────────────────────────────────────────────

class UserCreationForm(forms.ModelForm):
    """
    ساخت کاربر با شماره‌ی موبایل.

    فرم آماده‌ی جنگو روی ``username`` بنا شده و اینجا کار نمی‌کند.

    رمز برای مشتری اختیاری است (ورود پیامکی)؛ در آن حالت رمزِ
    غیرقابل‌استفاده ست می‌شود، که با «رمز خالی» فرق دارد. ولی **کارکنان
    رمز لازم دارند**: صفحه‌ی ورود کارکنان فقط با رمز کار می‌کند و
    کارمندِ بی‌رمز راهی به تابلو ندارد.
    """

    password1 = forms.CharField(
        label='رمز عبور', widget=forms.PasswordInput, required=False,
        help_text='برای کارکنان الزامی است. برای مشتری‌ای که فقط با کد پیامکی '
                  'وارد می‌شود خالی بگذارید.')
    password2 = forms.CharField(
        label='تکرار رمز عبور', widget=forms.PasswordInput, required=False)

    class Meta:
        model = User
        fields = ('phone', 'username', 'first_name', 'last_name', 'email', 'role')

    def clean_phone(self):
        return normalize_phone(self.cleaned_data['phone'])

    def clean(self):
        cleaned = super().clean()
        first = cleaned.get('password1')
        second = cleaned.get('password2')
        if first != second:
            self.add_error('password2', 'دو رمز یکسان نیستند.')
        if cleaned.get('role') in STAFF_ROLES and not first:
            self.add_error('password1', 'کارکنان با رمز وارد تابلو می‌شوند؛ رمز بگذارید.')
        elif first:
            # همان قاعده‌ی ثبت‌نام و تغییر رمز (AUTH_PASSWORD_VALIDATORS)
            try:
                validate_password(first)
            except forms.ValidationError as error:
                self.add_error('password1', error)
        return cleaned

    def save(self, commit=True):
        user = super().save(commit=False)
        password = self.cleaned_data.get('password1')
        if password:
            user.set_password(password)
        else:
            user.set_unusable_password()
        if commit:
            user.save()
        return user


class UserChangeForm(forms.ModelForm):
    """
    ویرایش کاربر.

    رمز به‌صورت هش نمایش داده می‌شود و از این فرم قابل تغییر نیست؛
    تغییرش از لینک جداگانه انجام می‌شود تا تصادفی بازنویسی نشود.
    """

    password = ReadOnlyPasswordHashField(
        label='رمز عبور',
        help_text='رمز ذخیره نمی‌شود، فقط هشش. برای تغییر، دکمه‌ی «تغییر رمز» را بزنید.')

    class Meta:
        model = User
        # کلید دومرحله‌ای عمداً بیرون است — نه دیدنی، نه ویرایش‌شدنی.
        exclude = ('totp_secret',)

    def clean_phone(self):
        return normalize_phone(self.cleaned_data['phone'])


# ─────────────────────────────────────────────────────────────────────
#  اینلاین
# ─────────────────────────────────────────────────────────────────────

class AddressInline(admin.StackedInline):
    """
    نشانی‌های کاربر.

    دسترسی از خودِ صفحه‌ی کاربر پیروی می‌کند، نه از مجوزهای ریز جنگو —
    وگرنه مدیری که سوپریوزر نیست (و مجوز ``change_address`` ندارد)
    نشانی‌ها را اصلاً نمی‌دید. «حذف» اینجا حذف نرم است.
    """

    model = Address
    extra = 0
    fields = (
        ('title', 'is_default'),
        ('receiver_name', 'receiver_phone'),
        ('province', 'city', 'district'),
        'line',
        ('plaque', 'unit', 'postal_code'),
    )

    def get_queryset(self, request):
        # نشانی حذف‌شده در فهرست کاربر نمایش داده نمی‌شود، ولی در
        # دیتابیس می‌ماند چون سفارش‌های قدیمی از رویش ساخته شده‌اند.
        return super().get_queryset(request).filter(deleted_at__isnull=True)

    def _parent(self):
        return self.admin_site._registry[User]

    def has_view_permission(self, request, obj=None):
        return self._parent().has_view_permission(request, obj)

    def has_change_permission(self, request, obj=None):
        return self._parent().has_change_permission(request, obj)

    def has_add_permission(self, request, obj=None):
        return self._parent().has_change_permission(request, obj)

    def has_delete_permission(self, request, obj=None):
        return self._parent().has_change_permission(request, obj)


# ─────────────────────────────────────────────────────────────────────
#  کاربر
# ─────────────────────────────────────────────────────────────────────

@admin.register(User)
class UserAdmin(RoleRestrictedMixin, BaseUserAdmin):
    manager_only = True

    form = UserChangeForm
    add_form = UserCreationForm

    list_display = ('phone_fa', 'full_name', 'username', 'role', 'panel_access',
                    'tier_name', 'orders_count_fa', 'spent', 'last_login', 'is_active')
    list_filter = ('role', 'is_active', 'is_staff', 'is_superuser', 'is_phone_verified',
                   'sms_opt_in', 'totp_enabled', 'created_at')
    search_fields = ('phone', 'username', 'first_name', 'last_name', 'email')
    ordering = ('-created_at',)
    list_per_page = 40
    inlines = (AddressInline,)

    fieldsets = (
        (None, {'fields': ('phone', 'username', 'password')}),
        ('مشخصات', {'fields': (('first_name', 'last_name'), 'email',
                               ('birth_year', 'birth_month', 'birth_day'))}),
        ('نقش و دسترسی', {
            'fields': ('role', 'is_active', 'is_phone_verified',
                       'is_staff', 'is_superuser', 'groups', 'user_permissions'),
            'description': '«نقش» راه ورود به تابلوی سفارش‌ها را تعیین می‌کند '
                           '(ادمین قنادی یا مدیر). «دسترسی به پنل جنگو» فقط همین '
                           'صفحه‌های مدیریت را باز می‌کند.',
        }),
        ('اطلاع‌رسانی', {'fields': (('sms_opt_in', 'email_opt_in'),)}),
        ('باشگاه رُزِت', {'fields': ('tier_summary', 'orders_count',
                                    'total_spent_rial', 'last_order_at')}),
        ('امنیت', {'classes': ('collapse',),
                   'fields': ('totp_enabled', 'last_login', 'last_login_ip',
                              'anonymized_at')}),
        ('زمان', {'classes': ('collapse',), 'fields': ('created_at', 'updated_at')}),
    )

    add_fieldsets = (
        (None, {
            'classes': ('wide',),
            'fields': ('phone', 'role', ('first_name', 'last_name'),
                       'email', 'username', 'password1', 'password2'),
            'description': 'برای کارکنان نام کاربری و رمز بگذارید؛ ورود کارکنان '
                           'از /staff/login/ با همین دو است.',
        }),
    )

    readonly_fields = ('last_login', 'created_at', 'updated_at', 'tier_summary',
                       'orders_count', 'total_spent_rial', 'last_order_at',
                       'last_login_ip', 'anonymized_at')
    filter_horizontal = ('groups', 'user_permissions')

    # ── ستون‌ها ────────────────────────────────────────────────────

    @admin.display(description='شماره', ordering='phone')
    def phone_fa(self, obj):
        return to_persian_digits(obj.phone)

    @admin.display(description='نام')
    def full_name(self, obj):
        return obj.full_name or '—'

    @admin.display(description='تابلوی کارکنان', boolean=True)
    def panel_access(self, obj):
        return obj.can_use_staff_panel

    @admin.display(description='پله')
    def tier_name(self, obj):
        return obj.tier['name']

    @admin.display(description='سفارش', ordering='orders_count')
    def orders_count_fa(self, obj):
        return to_persian_digits(obj.orders_count)

    @admin.display(description='مجموع خرید', ordering='total_spent_rial')
    def spent(self, obj):
        return f'{format_toman(obj.total_spent_rial)} تومان'

    @admin.display(description='وضعیت باشگاه')
    def tier_summary(self, obj):
        tier = obj.tier
        if tier['next_at'] is None:
            return format_html('<b>{}</b> — بالاترین پله', tier['name'])
        return format_html(
            '<b>{}</b> — {} سفارش تا پله‌ی بعد',
            tier['name'], to_persian_digits(obj.orders_to_next_tier))

    # ── جست‌وجو ────────────────────────────────────────────────────

    def get_search_results(self, request, queryset, search_term):
        # مدیر با کیبورد فارسی «۰۹۱۵…» تایپ می‌کند و شماره لاتین ذخیره
        # شده؛ بدون این، جست‌وجوی شماره هیچ‌وقت چیزی پیدا نمی‌کرد.
        return super().get_search_results(request, queryset, fix_digits(search_term))

    def get_inlines(self, request, obj):
        # فرم ساخت فقط شماره و نقش و رمز می‌خواهد؛ نشانی بعداً.
        return self.inlines if obj is not None else ()

    # ── دسترسی ─────────────────────────────────────────────────────

    def has_change_permission(self, request, obj=None):
        return (super().has_change_permission(request, obj)
                and can_edit_user(request, obj))

    def has_delete_permission(self, request, obj=None):
        # حذف کاربر یعنی از دست رفتن ارجاع سفارش‌ها. مسیر درست
        # «ناشناس‌سازی» است، نه DELETE.
        return False

    def get_readonly_fields(self, request, obj=None):
        fields = list(super().get_readonly_fields(request, obj))
        if not _is_superuser(request):
            # نقش همچنان قابل انتخاب است، ولی فقط تا «ادمین قنادی» —
            # formfield_for_choice_field. بقیه‌ی درهای دسترسی بسته‌اند.
            fields += ['is_superuser', 'is_staff', 'groups', 'user_permissions',
                       'totp_enabled']
        if obj is not None and obj.pk == request.user.pk:
            fields += ['role', 'is_active', 'is_staff', 'is_superuser']
        return tuple(dict.fromkeys(fields))

    def formfield_for_choice_field(self, db_field, request, **kwargs):
        if db_field.name == 'role' and not _is_superuser(request):
            kwargs['choices'] = [(value, label) for value, label in Role.choices
                                 if value != Role.MANAGER]
        return super().formfield_for_choice_field(db_field, request, **kwargs)

    # ── اکشن ───────────────────────────────────────────────────────

    @admin.action(description='ناشناس‌سازی حساب‌های انتخاب‌شده')
    def anonymize(self, request, queryset):
        """
        همان ``User.anonymize()`` که پنل کاربری صدا می‌زند.

        این‌ها کنار گذاشته می‌شوند و علتشان گفته می‌شود: خودِ شما،
        سوپریوزر و مدیرها (مگر برای سوپریوزر)، و کسی که سفارش در جریان
        دارد — کیکی در فر نباید صاحبِ بی‌نام‌ونشان پیدا کند.
        """
        done, skipped = 0, []
        for user in queryset.filter(anonymized_at__isnull=True):
            if user.pk == request.user.pk:
                skipped.append(f'{user} (حساب خودتان)')
            elif user.is_superuser or not can_edit_user(request, user):
                skipped.append(f'{user} (دسترسی ندارید)')
            elif user.has_open_orders():
                skipped.append(f'{user} (سفارش در جریان)')
            else:
                user.anonymize()
                done += 1
        self.message_user(request, f'{to_persian_digits(done)} حساب ناشناس شد. '
                                   'سفارش‌ها دست‌نخورده ماندند.')
        if skipped:
            self.message_user(request, 'کنار گذاشته شد: ' + '، '.join(skipped),
                              level=messages.WARNING)

    actions = ('anonymize',)


@admin.register(Address)
class AddressAdmin(RoleRestrictedAdmin):
    manager_only = False
    kitchen_readonly = True

    list_display = ('title', 'user', 'city', 'receiver_name', 'is_default', 'deleted_at')
    list_filter = ('city', 'is_default', 'province')
    search_fields = ('title', 'line', 'receiver_name', 'receiver_phone',
                     'user__phone', 'user__first_name', 'user__last_name')
    autocomplete_fields = ('user',)
    list_select_related = ('user',)


@admin.register(Favorite)
class FavoriteAdmin(RoleRestrictedAdmin):
    list_display = ('user', 'product', 'created_at')
    search_fields = ('user__phone', 'product__name')
    autocomplete_fields = ('user', 'product')
    list_select_related = ('user', 'product')
    date_hierarchy = 'created_at'


@admin.register(OTPCode)
class OTPCodeAdmin(ReadOnlyAdmin):
    """
    فقط خواندنی — و ستون ``code_hash`` عمداً در فهرست نیست.

    خودِ کد اصلاً ذخیره نمی‌شود؛ حتی سوپر ادمین هم نمی‌تواند کد کسی را
    ببیند و با آن وارد حسابش شود.
    """

    list_display = ('phone_fa', 'purpose', 'created_at', 'expires_at',
                    'used_at', 'attempts')
    list_filter = ('purpose', 'created_at')
    search_fields = ('phone',)
    date_hierarchy = 'created_at'

    @admin.display(description='شماره', ordering='phone')
    def phone_fa(self, obj):
        return to_persian_digits(obj.phone)


@admin.register(LoginAttempt)
class LoginAttemptAdmin(ReadOnlyAdmin):
    list_display = ('created_at', 'phone', 'succeeded', 'is_staff_panel',
                    'ip', 'failure_reason')
    list_filter = ('succeeded', 'is_staff_panel', 'created_at')
    search_fields = ('phone', 'ip')
    date_hierarchy = 'created_at'
    list_select_related = ('user',)
