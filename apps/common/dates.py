"""
تاریخ شمسی.

کل سایت تاریخ را شمسی نشان می‌دهد — «۱۴۰۴/۰۶/۰۹». دیتابیس میلادی ذخیره
می‌کند (همان کاری که هر دیتابیسی باید بکند: یک نقطه‌ی زمانی، بدون تقویم)
و تبدیل فقط در مرز نمایش انجام می‌شود.

کتابخانه‌ی جدا لازم نشد: الگوریتم تبدیل سی خط است و همین‌جا می‌ماند، پس
یک وابستگی کمتر برای چیزی که هرگز عوض نمی‌شود.
"""

from .text import to_persian_digits

GREGORIAN_DAYS = (0, 31, 59, 90, 120, 151, 181, 212, 243, 273, 304, 334)

MONTHS = ('فروردین', 'اردیبهشت', 'خرداد', 'تیر', 'مرداد', 'شهریور',
          'مهر', 'آبان', 'آذر', 'دی', 'بهمن', 'اسفند')

# ``date.weekday()`` دوشنبه را صفر می‌گیرد؛ این جدول با همان اندیس خوانده
# می‌شود، پس ترتیبش از دوشنبه شروع است نه از شنبه.
WEEKDAYS = ('دوشنبه', 'سه‌شنبه', 'چهارشنبه', 'پنجشنبه',
            'جمعه', 'شنبه', 'یکشنبه')


def _is_leap(year):
    return (year % 4 == 0 and year % 100 != 0) or year % 400 == 0


def to_jalali(value):
    """``date`` یا ``datetime`` میلادی → سه‌تایی ``(سال، ماه، روز)`` شمسی."""
    year, month, day = value.year, value.month, value.day

    # شماره‌ی روز از ابتدای ۱۶۰۰ میلادی؛ مبنای مشترک هر دو تقویم.
    offset = year - 1600
    days = (365 * offset + (offset + 3) // 4
            - (offset + 99) // 100 + (offset + 399) // 400)
    days += GREGORIAN_DAYS[month - 1] + day - 1
    if month > 2 and _is_leap(year):
        days += 1

    # ۷۹ روز فاصله‌ی ۱ فروردین ۹۷۹ تا ۱ ژانویه‌ی ۱۶۰۰.
    days -= 79
    cycles, days = divmod(days, 12053)          # هر ۳۳ سال، یک دوره‌ی کامل
    jyear = 979 + 33 * cycles + 4 * (days // 1461)
    days %= 1461
    if days >= 366:
        jyear += (days - 1) // 365
        days = (days - 1) % 365

    # شش ماه اول ۳۱ روزه‌اند، شش ماه دوم ۳۰ روزه.
    if days < 186:
        jmonth, jday = 1 + days // 31, 1 + days % 31
    else:
        days -= 186
        jmonth, jday = 7 + days // 30, 1 + days % 30
    return jyear, jmonth, jday


def jalali_date(value, digits='fa'):
    """«۱۴۰۴/۰۶/۰۹»"""
    if value is None:
        return ''
    year, month, day = to_jalali(value)
    text = f'{year}/{month:02d}/{day:02d}'
    return to_persian_digits(text) if digits == 'fa' else text


def jalali_long(value):
    """«پنجشنبه ۱۴۰۴/۰۶/۱۲» — همان شکلی که کارت «سفارش در جریان» می‌خواهد."""
    if value is None:
        return ''
    return f'{WEEKDAYS[value.weekday()]} {jalali_date(value)}'
