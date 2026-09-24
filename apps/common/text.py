"""
نرمال‌سازی متن فارسی.

سه مشکل را حل می‌کند که در هر سایت فارسی هست و همیشه دیر پیدا می‌شود:

۱. «ی» و «ک» عربی (ي, ك) با فارسی (ی, ک) فرق دارند و
   کاربر هر دو را تایپ می‌کند. «کيک» و «کیک» برای دیتابیس دو رشته‌ی
   متفاوت‌اند.
۲. ارقام عربی-هندی و فارسی و لاتین — شماره‌ی موبایل با کیبورد فارسی
   «۰۹۱۲…» درمی‌آید و با `CharField(max_length=11)` هم جا می‌شود و هم
   غلط است.
۳. نویسه‌های نامرئی: نیم‌فاصله، ZWNJ، اعراب. در نمایش لازم‌اند، در
   مقایسه مزاحم.

قاعده: ذخیره با شکل تمیز، مقایسه با شکل نرمال‌شده — و نرمال‌سازی روی
**هر دو طرف** مقایسه اعمال شود، وگرنه بی‌فایده است.
"""

import re
import unicodedata

# ی و ک عربی → فارسی، به‌علاوه‌ی چند جایگزینی مرسوم
LETTERS = {
    'ي': 'ی',   # ARABIC YEH        → FARSI YEH
    'ى': 'ی',   # ALEF MAKSURA      → FARSI YEH
    'ك': 'ک',   # ARABIC KAF        → KEHEH
    'ۀ': 'ه',   # HEH WITH YEH ABOVE→ HEH
    'ة': 'ه',   # TEH MARBUTA       → HEH
    'أ': 'ا',   # ALEF WITH HAMZA
    'إ': 'ا',
    'آ': 'ا',
}

DIGITS = {}
for index in range(10):
    DIGITS[chr(0x06F0 + index)] = str(index)   # ارقام فارسی  ۰۱۲۳
    DIGITS[chr(0x0660 + index)] = str(index)   # ارقام عربی   ٠١٢٣

# اعراب و نویسه‌های کنترلی جهت
MARKS = re.compile('[ً-ٰٟ‌‍‎‏﻿]')

SPACES = re.compile(r'\s+')


def fix_letters(value):
    """ی و ک عربی را فارسی می‌کند. برای ذخیره‌سازی هم استفاده می‌شود."""
    if not value:
        return value
    return ''.join(LETTERS.get(char, char) for char in value)


def fix_digits(value):
    """ارقام فارسی و عربی را به لاتین برمی‌گرداند."""
    if not value:
        return value
    return ''.join(DIGITS.get(char, char) for char in value)


def to_persian_digits(value):
    """لاتین → فارسی. فقط برای نمایش."""
    table = {str(index): chr(0x06F0 + index) for index in range(10)}
    return ''.join(table.get(char, char) for char in str(value))


def normalize(value):
    """
    شکل قابل‌مقایسه: بدون اعراب، بدون نیم‌فاصله، حروف یکدست، ارقام لاتین،
    فاصله‌های جمع‌شده، حروف کوچک.

    خروجی این تابع در ``Product.search_norm`` ذخیره می‌شود و عبارت
    جست‌وجوی کاربر هم پیش از مقایسه از همین می‌گذرد.
    """
    if not value:
        return ''
    value = unicodedata.normalize('NFKC', str(value))
    value = fix_letters(value)
    value = fix_digits(value)
    value = MARKS.sub('', value)
    value = SPACES.sub(' ', value)
    return value.strip().lower()


def parse_int(value, default=None):
    """
    عددِ ورودی کاربر، یا ``default``.

    هر چیزی که عدد نیست — رشته‌ی خالی، ``None``، متن — به جای انداختن
    استثنا، ``default`` می‌دهد. بدون این، یک ``filter(pk='')`` در جنگو
    ``ValueError`` می‌اندازد و فرمِ ناقصِ کاربر به خطای ۵۰۰ تبدیل
    می‌شود، نه به یک پیام قابل‌فهم.

    ارقام فارسی هم پذیرفته می‌شوند.
    """
    if value is None or value is True or value is False:
        return default
    try:
        return int(fix_digits(str(value)).strip())
    except (TypeError, ValueError):
        return default


def normalize_phone(value):
    """
    شماره‌ی موبایل ایران را به شکل ``09xxxxxxxxx`` برمی‌گرداند.

    ورودی‌های رایجی که باید یکی شوند:
    ``۰۹۱۲۳۴۵۶۷۸۹`` · ``+98 912 345 6789`` · ``0098912…`` · ``912…``
    """
    if not value:
        return ''
    value = fix_digits(str(value))
    value = re.sub(r'[^\d+]', '', value)
    value = re.sub(r'^\+?98', '0', value)
    value = re.sub(r'^0098', '0', value)
    if len(value) == 10 and value.startswith('9'):
        value = '0' + value
    return value
