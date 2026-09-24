"""
فیلترهای قالب.

همان دو کاری که در تمپلیت ساکن، جاوااسکریپت انجام می‌داد: تبدیل ریال به
تومان و فارسی‌کردن ارقام. حالا سمت سرور انجام می‌شود تا صفحه بدون
جاوااسکریپت هم درست دیده شود.
"""

import json

from django import template
from django.utils.safestring import mark_safe

from django.utils import timezone

from apps.common import money, text
from apps.common.dates import jalali_date

register = template.Library()


@register.filter
def toman(value):
    """۳۸۰۰۰۰۰ ریال → «۳۸۰٬۰۰۰» برای نمایش."""
    return money.format_toman(value)


@register.filter
def toman_plain(value):
    """
    ۳۸۰۰۰۰۰ ریال → «380000».

    برای ``data-price`` روی کارت محصول. جاوااسکریپت سبد همین را
    می‌خواند، پس باید عدد لاتین و بدون جداکننده باشد.
    """
    return '' if value in (None, '') else money.rial_to_toman(value)


@register.filter
def fa(value):
    """ارقام لاتین → فارسی."""
    return text.to_persian_digits(value)


@register.filter
def get_item(mapping, key):
    """{{ dict|get_item:key }} — قالب جنگو کلید متغیر را خودش نمی‌خواند."""
    try:
        return mapping.get(key, '')
    except AttributeError:
        return ''


@register.filter
def fa_int(value):
    """۳۸۰۰۰۰ → «۳۸۰٬۰۰۰» — عدد صحیح با جداکننده‌ی فارسی (مثل toLocaleString)."""
    try:
        number = int(value)
    except (TypeError, ValueError):
        return ''
    return text.to_persian_digits(f'{number:,}'.replace(',', '٬'))


@register.filter
def jalali(value):
    """تاریخ یا زمان ← «۱۴۰۵/۰۶/۳۱» به وقت محلی."""
    if not value:
        return ''
    if hasattr(value, 'hour'):
        value = timezone.localtime(value)
    return jalali_date(value)


@register.filter
def fa1(value):
    """۴٫۵ — یک رقم اعشار با جداکننده‌ی فارسی؛ همان fa1 جاوااسکریپت."""
    try:
        number = float(value)
    except (TypeError, ValueError):
        return ''
    return text.to_persian_digits(f'{number:.1f}'.replace('.', '٫'))


# همان جایگزینی‌هایی که json_script جنگو انجام می‌دهد: متنی مثل
# «</script>» در نام محصول یا نظر مشتری نباید تگ را زودتر ببندد.
_JSON_ESCAPES = {ord('<'): '\\u003C', ord('>'): '\\u003E', ord('&'): '\\u0026'}


@register.simple_tag
def jsonld(data):
    """
    داده‌ی ساختاریافته برای گوگل: ``<script type="application/ld+json">``.

    ``json_script`` جنگو نوع را ``application/json`` می‌گذارد و شناسه
    می‌خواهد؛ گوگل فقط ``application/ld+json`` را می‌خواند.
    """
    text_ = json.dumps(data, ensure_ascii=False, separators=(',', ':'))
    return mark_safe('<script type="application/ld+json">'
                     f'{text_.translate(_JSON_ESCAPES)}</script>')
