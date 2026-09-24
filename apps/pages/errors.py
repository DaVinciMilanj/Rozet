"""
صفحه‌های خطا — ۴۰۴ و ۵۰۰.

جنگو این دو را فقط وقتی نشان می‌دهد که ``DEBUG=False`` باشد؛ در حالت
توسعه صفحه‌ی زرد دیباگ می‌آید. برای دیدنشان در توسعه:

    /_errors/404/   و   /_errors/500/     (فقط وقتی DEBUG روشن است)

دو صفحه عمداً دو جور ساخته شده‌اند:

* **۴۰۴** یک صفحه‌ی کامل سایت است — هدر، سبد، فوتر و چند محصول
  پیشنهادی. وقتی صفحه‌ای پیدا نمی‌شود، سایت سالم است و بهترین کار این
  است که آدم را به جای درستی برساند.

* **۵۰۰** یعنی خودِ سایت جایی شکسته — شاید دیتابیس، شاید یک ماژول.
  پس این صفحه به هیچ‌چیز تکیه نمی‌کند: نه دیتابیس، نه context
  processorها (سبد خرید از دیتابیس خوانده می‌شود)، نه قالب پایه. CSS
  درون خودش است. اگر حتی رندرِ قالب هم شکست بخورد، یک HTML ثابت
  برمی‌گردد — صفحه‌ی خطایی که خودش خطا بدهد، بدترین حالت ممکن است.
"""

import logging

from django.conf import settings
from django.db import DatabaseError
from django.http import HttpResponseServerError
from django.shortcuts import render
from django.template import loader

from apps.catalog.favorites import favorite_ids
from apps.catalog.models import Product
from apps.common import seo

from .views import _cards

logger = logging.getLogger(__name__)

SUGGESTIONS = 3

# آخرین خط دفاع: اگر حتی قالب ۵۰۰ رندر نشد.
FALLBACK_500 = (
    '<!DOCTYPE html><html lang="fa" dir="rtl"><head><meta charset="utf-8">'
    '<meta name="viewport" content="width=device-width,initial-scale=1">'
    '<title>خطای موقت — رُزِت</title></head>'
    '<body style="margin:0;min-height:100vh;display:grid;place-items:center;'
    'background:#FAF6F0;color:#2A1B16;font-family:Tahoma,system-ui,sans-serif;'
    'text-align:center;padding:1.5rem">'
    '<div><h1 style="font-size:1.4rem">مشکلی موقت پیش آمد</h1>'
    '<p style="color:#7A5E52;line-height:2">تقصیر شما نیست. چند لحظه‌ی دیگر دوباره امتحان کنید.</p>'
    '<p><a href="/" style="color:#BA4E64">بازگشت به صفحه‌ی اصلی</a></p></div>'
    '</body></html>'
)


def not_found(request, exception=None):
    """۴۰۴ — با چند محصول پرفروش، تا بن‌بست نباشد."""
    try:
        suggestions = list(_cards(Product.objects.in_stock(), SUGGESTIONS))
        liked = favorite_ids(request.user)
    except DatabaseError:
        # ۴۰۴ نباید به‌خاطر پیشنهادها به ۵۰۰ تبدیل شود.
        logger.exception('پیشنهادهای صفحه‌ی ۴۰۴ خوانده نشد')
        suggestions, liked = [], set()
    return render(request, '404.html', {
        'suggestions': suggestions,
        'favorite_ids': liked,
        'request_path': request.path,
        # ۴۰۴ نباید در گوگل بنشیند؛ پیوندهایش اما دنبال شوند.
        'seo': seo.build(
            request,
            title=seo.page_title('این صفحه پیدا نشد'),
            description=('صفحه‌ای که دنبالش بودید در رُزِت پیدا نشد. از همین‌جا به کیک‌ها، '
                         'شیرینی‌ها و سفارش کیک اختصاصی برگردید.'),
            robots=seo.ROBOTS_NOINDEX),
    }, status=404)


def server_error(request):
    """۵۰۰ — بدون دیتابیس و بدون context processor."""
    try:
        # render بدون request: context processorها اجرا نمی‌شوند، پس
        # هیچ کوئری‌ای زده نمی‌شود. فقط اطلاعات ثابت کافه از تنظیمات.
        body = loader.get_template('500.html').render({'CAFE': settings.CAFE})
    except Exception:                                    # noqa: BLE001
        logger.exception('قالب ۵۰۰ رندر نشد؛ نسخه‌ی ثابت برگشت')
        body = FALLBACK_500
    return HttpResponseServerError(body)
