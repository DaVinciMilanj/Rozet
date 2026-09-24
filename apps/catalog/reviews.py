"""
ثبت نظر روی محصول — فرم «نظر شما» در صفحه‌ی جزئیات.

در تمپلیت، فرم نظر را فقط به فهرست همان صفحه اضافه می‌کرد و با رفرش
گم می‌شد. اینجا ذخیره می‌شود، ولی **تأییدنشده**: تا مدیر از پنل تأییدش
نکند، نه در فهرست عمومی می‌آید و نه در میانگین ستاره‌ها
(``Product.refresh_rating`` فقط تأییدشده‌ها را می‌شمارد).

هر کاربر روی هر محصول یک نظر دارد (قید دیتابیس). نظر دوم همان قبلی را
به‌روز می‌کند و دوباره به صف تأیید می‌رود — ویرایشِ نظرِ تأییدشده نباید
بی‌بازبینی روی صفحه بنشیند.
"""

import json

from django.conf import settings
from django.http import JsonResponse
from django.views import View

from apps.common.text import parse_int

from .models import Product, Review

MAX_TEXT = 300          # همان شمارنده‌ی فرم (revLeft)


class ReviewSubmitView(View):
    """POST {product, rating, text} → {ok, pending}"""

    def post(self, request):
        if not request.user.is_authenticated:
            return JsonResponse({
                'ok': False,
                'auth': False,
                'error': 'برای ثبت نظر وارد شوید.',
                'login': f'{settings.LOGIN_URL}?next={request.META.get("HTTP_REFERER", "/")}',
            }, status=401)

        try:
            data = json.loads(request.body or '{}')
        except (json.JSONDecodeError, UnicodeDecodeError):
            data = None
        if not isinstance(data, dict):
            return JsonResponse({'ok': False, 'error': 'درخواست نامعتبر است.'}, status=400)

        rating = parse_int(data.get('rating'))
        if rating is None or not 1 <= rating <= 5:
            return JsonResponse({'ok': False, 'error': 'اول ستاره‌ها را انتخاب کنید.'},
                                status=400)

        product = Product.objects.live().filter(pk=parse_int(data.get('product'))).first()
        if product is None:
            return JsonResponse({'ok': False, 'error': 'محصول پیدا نشد.'}, status=404)

        Review.objects.update_or_create(
            product=product, user=request.user,
            defaults={'rating': rating,
                      'text': str(data.get('text') or '').strip()[:MAX_TEXT],
                      'is_approved': False})
        return JsonResponse({'ok': True, 'pending': True})
