"""
ابزار مشترک اندپوینت‌های JSON.

هر صفحه‌ی سایت یک اندپوینت دارد که روی ``action`` تقسیم می‌کند (سبد،
پرداخت، حساب، ورود، پنل کارکنان…). همه‌ی آن‌ها سه کار تکراری داشتند —
خواندن بدنه‌ی JSON، ساختن پاسخ خطا، و جواب به کاربرِ واردنشده — و هر
کدام نسخه‌ی خودش را نوشته بود. اینجا یک‌بار نوشته شده است.

قرارداد پاسخ در کل سایت یکی است:

    موفق   {"ok": true, ...}
    خطا    {"ok": false, "error": "پیام فارسی", ...}    با کد HTTP مناسب
"""

import json
from urllib.parse import urlencode

from django.conf import settings
from django.http import JsonResponse

BAD_REQUEST = 'درخواست نامعتبر است.'


def read_json(request):
    """
    بدنه‌ی درخواست به‌صورت دیکشنری، یا ``None`` اگر JSONِ معتبرِ شیء نبود.

    آرایه یا عدد هم JSON معتبر است ولی هیچ اندپوینتی آن را نمی‌خواهد؛
    بدون بررسی نوع، ``data.get`` روی لیست به خطای ۵۰۰ می‌رسید.
    """
    try:
        data = json.loads(request.body or b'{}')
    except (ValueError, UnicodeDecodeError):
        return None
    return data if isinstance(data, dict) else None


def ok(**payload):
    return JsonResponse({'ok': True, **payload})


def fail(message, status=400, **extra):
    return JsonResponse({'ok': False, 'error': message, **extra}, status=status)


def login_url(request):
    """نشانی صفحه‌ی ورود، با بازگشت به صفحه‌ای که کاربر از آن آمده."""
    back = request.META.get('HTTP_REFERER') or '/'
    return f'{settings.LOGIN_URL}?{urlencode({"next": back})}'


def auth_required(request, message='برای ادامه وارد حساب خود شوید.'):
    """
    ۴۰۱ برای کاربرِ واردنشده — نه ریدایرکت.

    ``fetch`` ریدایرکت را بی‌صدا دنبال می‌کند و HTML صفحه‌ی ورود را جای
    JSON تحویل می‌دهد؛ جاوااسکریپت آن‌وقت فقط «خطای ناشناخته» می‌بیند.
    ``auth: false`` و ``login`` به صفحه می‌گویند کاربر را کجا بفرستد.
    """
    return fail(message, status=401, auth=False, login=login_url(request))


def validation_message(error):
    """``ValidationError`` جنگو → یک جمله برای نمایش."""
    if hasattr(error, 'message_dict'):
        return ' '.join(message for messages in error.message_dict.values()
                        for message in messages)
    return ' '.join(error.messages)
