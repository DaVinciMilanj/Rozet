"""
اعتبارسنج‌های مشترک.
"""

import re

from django.core.exceptions import ValidationError
from django.utils.deconstruct import deconstructible

from .text import fix_digits

PHONE_RE = re.compile(r'^09\d{9}$')
POSTAL_RE = re.compile(r'^\d{10}$')
NATIONAL_RE = re.compile(r'^\d{10}$')


def validate_phone(value):
    """موبایل ایران، پس از تبدیل ارقام فارسی."""
    if not PHONE_RE.match(fix_digits(str(value))):
        raise ValidationError('شماره موبایل باید ۱۱ رقم و با ۰۹ شروع شود.')


def validate_landline(value):
    number = fix_digits(str(value))
    if not re.match(r'^0\d{9,10}$', number):
        raise ValidationError('شماره ثابت را با کد شهر وارد کنید.')


def validate_postal_code(value):
    if not POSTAL_RE.match(fix_digits(str(value))):
        raise ValidationError('کد پستی باید ۱۰ رقم باشد.')


def validate_national_id(value):
    """
    کد ملی با رقم کنترلی.

    ده رقم بودن کافی نیست: «۱۱۱۱۱۱۱۱۱۱» ده رقم است و کد ملی نیست.
    """
    number = fix_digits(str(value))
    if not NATIONAL_RE.match(number) or len(set(number)) == 1:
        raise ValidationError('کد ملی نامعتبر است.')
    check = int(number[9])
    total = sum(int(number[index]) * (10 - index) for index in range(9))
    remainder = total % 11
    valid = check == remainder if remainder < 2 else check == 11 - remainder
    if not valid:
        raise ValidationError('کد ملی نامعتبر است.')


@deconstructible
class MaxFileSize:
    """
    سقف حجم فایل.

    ``deconstructible`` لازم است وگرنه هر بار که مقدارش عوض شود، مهاجرت
    نمی‌تواند آن را سریال کند.
    """

    def __init__(self, megabytes):
        self.megabytes = megabytes

    def __call__(self, file):
        if file.size > self.megabytes * 1024 * 1024:
            raise ValidationError(f'حجم فایل نباید از {self.megabytes} مگابایت بیشتر باشد.')

    def __eq__(self, other):
        return isinstance(other, MaxFileSize) and self.megabytes == other.megabytes


validate_image_size = MaxFileSize(5)
