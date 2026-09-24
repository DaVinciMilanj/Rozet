"""
پول.

قاعده‌ی کل پروژه: **همه چیز ریال ذخیره می‌شود.**

دلیلش یک باگ گران است. درگاه‌های ایرانی مبلغ را به ریال می‌گیرند، ولی کل
تمپلیت «تومان» نشان می‌دهد. اگر عدد تومانی مستقیم به درگاه برود، کیک
۳۸۰٬۰۰۰ تومانی ۳۸٬۰۰۰ تومان فاکتور می‌شود — و چون تراکنش موفق است، هیچ
خطایی هم دیده نمی‌شود.

برای همین نام هر ستون پولی به ``_rial`` ختم می‌شود. هر جا این پسوند
نیست، عدد پول نیست. تبدیل فقط در دو مرز اتفاق می‌افتد: نمایش به کاربر، و
گرفتن عدد از مدیر در پنل.
"""

from django.conf import settings


def toman_to_rial(value):
    if value in (None, ''):
        return None
    return int(round(float(value) * settings.RIAL_PER_TOMAN))


def rial_to_toman(value):
    if value in (None, ''):
        return None
    return int(value) // settings.RIAL_PER_TOMAN


def format_toman(rial, digits='fa'):
    """
    ریال را برای نمایش به تومانِ سه‌رقم‌جداشده تبدیل می‌کند.

    خروجی: ``۳۸۰٬۰۰۰`` — با جداکننده‌ی فارسی (U+066C)، نه کاما.
    """
    if rial in (None, ''):
        return ''
    text = f'{rial_to_toman(rial):,}'.replace(',', '٬')
    if digits == 'fa':
        table = {str(index): chr(0x06F0 + index) for index in range(10)}
        text = ''.join(table.get(char, char) for char in text)
    return text
