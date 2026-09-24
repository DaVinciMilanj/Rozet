"""
ابزارهای مشترک پنل مدیریت.

دو مسئله را یک‌بار حل می‌کند:

۱. **ریال در دیتابیس، تومان در فرم.** مدیر تومان می‌بیند و تومان تایپ
   می‌کند؛ ذخیره ریال است. بدون این، یا مدیر باید هر بار یک صفر اضافه
   کند — که بالاخره یک روز یادش می‌رود — یا باید ستون‌ها را تومانی کرد و
   موقع رفتن به درگاه ضرب کرد، که خطای بدتری است.

۲. **دسترسی بر اساس نقش.** ادمین قنادی نباید قیمت عوض کند یا محصول
   بسازد؛ فقط سفارش‌ها و موجودی. این با گروه‌های جنگو هم می‌شود ولی
   گروه‌ها دستی ساخته می‌شوند و یادِ کسی می‌رود.
"""

from django import forms
from django.contrib import admin
from django.db import models

from apps.common.money import format_toman, rial_to_toman, toman_to_rial
from apps.common.models import Pricing
from apps.common.text import fix_digits


class TomanFormField(forms.IntegerField):
    """
    فیلد فرم که تومان می‌گیرد و ریال می‌دهد.

    ارقام فارسی و جداکننده‌ها هم پذیرفته می‌شوند، چون مدیر با کیبورد
    فارسی تایپ می‌کند و «۳۸۰٬۰۰۰» دقیقاً همان چیزی است که در سایت
    می‌بیند.
    """

    def prepare_value(self, value):
        # مقدارِ آمده از دیتابیس عدد است و باید تومان نمایش داده شود؛
        # مقدارِ آمده از POST رشته است و همان‌طور که کاربر تایپ کرده باید
        # برگردد، وگرنه بعد از یک خطای اعتبارسنجی عدد دوباره تقسیم
        # می‌شود.
        if isinstance(value, int):
            return rial_to_toman(value)
        return value

    def to_python(self, value):
        if value not in self.empty_values:
            value = fix_digits(str(value))
            for separator in (',', '٬', '،', ' ', '‌'):
                value = value.replace(separator, '')
        value = super().to_python(value)
        # تبدیل در money.py است و باید همان‌جا بماند؛ ضرب و تقسیم دستی
        # در سه جای جدا یعنی روزی یکی‌شان از قلم می‌افتد.
        return toman_to_rial(value)


class TomanAdminMixin:
    """
    هر ستونی که نامش به ``_rial`` ختم شود، در فرم تومانی می‌شود.

    روی ``ModelAdmin`` و ``InlineModelAdmin`` هر دو کار می‌کند.
    """

    def formfield_for_dbfield(self, db_field, request, **kwargs):
        if isinstance(db_field, models.BigIntegerField) and db_field.name.endswith('_rial'):
            label = str(db_field.verbose_name).replace('ریال', 'تومان')
            return TomanFormField(
                label=label,
                required=not db_field.blank,
                initial=db_field.get_default() if db_field.has_default() else None,
                help_text=db_field.help_text or 'به تومان وارد کنید.',
                min_value=0,
            )
        return super().formfield_for_dbfield(db_field, request, **kwargs)


def toman_column(field_name, label, ordering=None):
    """ستون لیست که مبلغ را تومانی و با ارقام فارسی نشان می‌دهد."""

    @admin.display(description=label, ordering=ordering or field_name)
    def column(self, obj):
        return format_toman(getattr(obj, field_name))

    return column


class RoleRestrictedMixin:
    """
    دسترسی بر اساس نقش.

    ``manager_only`` یعنی ادمین قنادی این بخش را اصلاً نمی‌بیند.
    ``kitchen_readonly`` یعنی می‌بیند ولی فقط می‌خواند.

    میکسین جداست چون ``UserAdmin`` باید از ``BaseUserAdmin`` ارث ببرد و
    نمی‌تواند از یک ``ModelAdmin`` دیگر هم ارث ببرد.
    """

    manager_only = True
    kitchen_readonly = False

    def _is_manager(self, request):
        user = request.user
        return user.is_superuser or getattr(user, 'is_manager', False)

    def _is_kitchen(self, request):
        return getattr(request.user, 'is_kitchen', False)

    def has_module_permission(self, request):
        if self._is_manager(request):
            return True
        if self._is_kitchen(request) and not self.manager_only:
            return True
        return False

    def has_view_permission(self, request, obj=None):
        return self.has_module_permission(request)

    def has_add_permission(self, request):
        return self._is_manager(request)

    def has_change_permission(self, request, obj=None):
        if self._is_manager(request):
            return True
        return self._is_kitchen(request) and not self.manager_only and not self.kitchen_readonly

    def has_delete_permission(self, request, obj=None):
        return self._is_manager(request)


class RoleRestrictedAdmin(RoleRestrictedMixin, admin.ModelAdmin):
    """پایه‌ی بیشتر ادمین‌های پروژه."""


class ReadOnlyAdmin(RoleRestrictedAdmin):
    """
    جدول‌هایی که فقط خوانده می‌شوند.

    لاگ ورود، تاریخچه‌ی وضعیت، کد یک‌بارمصرف. اینها سند هستند؛ ویرایش‌شان
    یعنی سند بی‌اعتبار.
    """

    def has_add_permission(self, request):
        return False

    def has_change_permission(self, request, obj=None):
        return False

    def has_delete_permission(self, request, obj=None):
        return False

    def get_readonly_fields(self, request, obj=None):
        return [field.name for field in self.model._meta.fields]


@admin.register(Pricing)
class PricingAdmin(TomanAdminMixin, RoleRestrictedAdmin):
    """
    نرخ‌ها — تک‌رکوردی، فقط دست مدیر.

    مبلغ‌ها تومانی نمایش داده و گرفته می‌شوند؛ ذخیره به ریال است.
    """

    fieldsets = (
        ('ارسال', {'fields': ('courier_enabled',
                              ('delivery_fee_rial', 'free_delivery_over_rial'),
                              'gift_wrap_rial')}),
        ('کیک اختصاصی', {'fields': (('custom_deposit_rial',
                                     'custom_print_fee_rial'),)}),
        ('مالیات', {
            'fields': (('vat_enabled', 'vat_percent'),),
            'description': 'نرخ را با حسابدار تأیید کنید. صفر ماندنش از عدد '
                           'اشتباه بهتر است — نرخ غلط روی همه‌ی فاکتورها می‌نشیند.',
        }),
    )
    readonly_fields = ('updated_at',)

    def has_add_permission(self, request):
        return self._is_manager(request) and not Pricing.objects.exists()

    def has_delete_permission(self, request, obj=None):
        return False
