"""
دو پرسش درباره‌ی خودِ درخواست که چند جای سایت می‌پرسند.
"""

from django.conf import settings
from django.utils.http import url_has_allowed_host_and_scheme


def client_ip(request):
    """
    IP واقعی کاربر.

    ``X-Forwarded-For`` را هر کسی می‌تواند بفرستد؛ اگر کورکورانه خوانده
    شود، کسی که رمز حدس می‌زند هر IP دلخواهی را در لاگ ورود می‌نشاند.
    پس فقط وقتی به آن اعتماد می‌شود که بدانیم پشت پروکسیِ خودمان
    (nginx) هستیم — ``TRUSTED_PROXY_COUNT`` در تنظیمات.

    هر پروکسی IPِ طرفِ مقابلش را به **انتهای** سرآیند اضافه می‌کند. پس با
    N پروکسیِ خودمان، N-امین مقدار از آخر همان کسی است که به اولین
    پروکسیِ ما وصل شده؛ هر چه جلوترش باشد را خودِ کاربر نوشته است.
    """
    proxies = getattr(settings, 'TRUSTED_PROXY_COUNT', 0)
    if proxies > 0:
        chain = [part.strip() for part in
                 request.META.get('HTTP_X_FORWARDED_FOR', '').split(',') if part.strip()]
        if len(chain) >= proxies:
            return chain[-proxies]
    return request.META.get('REMOTE_ADDR') or None


def safe_next(request, raw, default):
    """
    مقصد بعد از ورود، یا ``default``.

    بدون این بررسی، ``?next=https://elsewhere/`` یک ریدایرکت باز است:
    لینکی که به رُزِت ختم می‌شود ولی کاربر را — تازه پس از ورود موفق —
    به سایت دیگری می‌برد.
    """
    if raw and url_has_allowed_host_and_scheme(
            raw, allowed_hosts={request.get_host()}, require_https=request.is_secure()):
        return raw
    return default
