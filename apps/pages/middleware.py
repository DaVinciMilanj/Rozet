"""
۴۰۴ سایت، در حالت توسعه هم.

با ``DEBUG=True`` جنگو برای هر نشانیِ اشتباه صفحه‌ی زرد دیباگ خودش
(«Page not found at …») را نشان می‌دهد و ``handler404`` اصلاً صدا زده
نمی‌شود. خاموش‌کردن DEBUG هم راه نیست: آن‌وقت runserver دیگر CSS و
تصویر سرو نمی‌کند و کل سایت به‌هم‌ریخته دیده می‌شود.

این میان‌افزار فقط همان صفحه‌ی دیباگ ۴۰۴ را با صفحه‌ی ۴۰۴ سایت عوض
می‌کند. به چیزهای دیگر دست نمی‌زند:

* پاسخ ۴۰۴ که خودِ ویوها ساخته‌اند (JSON اندپوینت‌ها، «سفارش پیدا نشد»
  پنل کارکنان) — فقط صفحه‌ی دیباگِ خودِ جنگو شناخته و عوض می‌شود؛
* فایل‌های ``/static/`` و ``/media/`` — تصویرِ گم‌شده نباید یک صفحه‌ی
  کامل با کوئری دیتابیس بسازد؛
* خطای ۵۰۰ — در توسعه ردِ خطا (traceback) لازم است.

روی سرور واقعی (``DEBUG=False``) اصلاً بار نمی‌شود؛ آنجا خودِ جنگو
``handler404`` را صدا می‌زند. اگر صفحه‌ی دیباگ ۴۰۴ لازم شد (مثلاً برای
دیدن فهرست الگوهای نشانی)، در ``.env``:  ``DEBUG_ERROR_PAGES=False``
"""

from django.conf import settings
from django.core.exceptions import MiddlewareNotUsed

from .errors import not_found

# عنوان قالب technical_404 جنگو — تنها نشانه‌ی قطعی صفحه‌ی دیباگ ۴۰۴.
DEBUG_404_MARKER = b'<title>Page not found at '


class DebugNotFoundMiddleware:
    def __init__(self, get_response):
        if not (settings.DEBUG and getattr(settings, 'DEBUG_ERROR_PAGES', True)):
            raise MiddlewareNotUsed
        self.get_response = get_response
        self.skip = tuple(prefix for prefix in (settings.STATIC_URL, settings.MEDIA_URL)
                          if prefix)

    def __call__(self, request):
        response = self.get_response(request)
        if (response.status_code == 404
                and not getattr(response, 'streaming', False)
                and not request.path.startswith(self.skip)
                and response.get('Content-Type', '').startswith('text/html')
                and DEBUG_404_MARKER in response.content):
            return not_found(request)
        return response
