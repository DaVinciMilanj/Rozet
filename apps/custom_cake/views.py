"""
سرو تصاویر خصوصی کیک اختصاصی.

این تنها راه دیدن این فایل‌هاست. چون زیر ``PRIVATE_MEDIA_ROOT`` هستند،
وب‌سرور مستقیم سروشان نمی‌کند و حدس‌زدن URL به جایی نمی‌رسد.

دلیلش: بخشی از این عکس‌ها قرار است روی کیک چاپ شوند و معمولاً عکس
خانوادگی‌اند. عکس تولد بچه‌ی یک مشتری نباید با یک URL قابل‌حدس در دسترس
باشد.
"""

import mimetypes

from django.contrib.auth.decorators import login_required
from django.core.exceptions import PermissionDenied
from django.http import FileResponse, Http404
from django.shortcuts import get_object_or_404

from .models import CustomCakeImage

SAFE_TYPES = {'image/jpeg', 'image/png', 'image/webp'}


@login_required
def cake_image(request, pk):
    image = get_object_or_404(CustomCakeImage.objects.select_related('request'), pk=pk)
    user = request.user

    # همان قاعده‌ی ورود به پنل کارکنان: هر که تابلو را می‌بیند، باید
    # عکس نمونه‌ی کیکی را که می‌سازد هم ببیند.
    allowed = (user.can_use_staff_panel
               or (image.request.user_id and image.request.user_id == user.pk))
    if not allowed:
        raise PermissionDenied

    try:
        handle = image.image.open('rb')
    except FileNotFoundError:
        raise Http404('فایل روی دیسک نیست.')

    # فقط نوع‌های تصویریِ بی‌خطر نمایش داده می‌شوند. هر چیز دیگری — از
    # جمله فایلی که پیش از وارسیِ محتوا ذخیره شده — دانلود می‌شود، نه
    # اجرا: یک SVG اسکریپت‌دار که اینجا باز شود، با نشست کارمند اجرا
    # می‌شد.
    content_type = (image.content_type
                    or mimetypes.guess_type(image.image.name)[0] or '')
    inline = content_type in SAFE_TYPES
    response = FileResponse(handle, as_attachment=not inline,
                            content_type=content_type if inline else 'application/octet-stream')
    # مرورگر و پروکسی‌های میانی نباید این را کش کنند.
    response['Cache-Control'] = 'private, no-store'
    response['X-Content-Type-Options'] = 'nosniff'
    # لایه‌ی دوم: حتی اگر چیزی از بررسی‌ها رد شد، اینجا اسکریپتی اجرا نشود.
    response['Content-Security-Policy'] = "default-src 'none'; img-src 'self'; sandbox"
    return response
