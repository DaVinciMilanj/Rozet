"""
دکمه‌ی قلب — در هر جای سایت.

قلب در سه صفحه با سه پیاده‌سازی جدا بود و هر سه فقط یک کلاس CSS را
عوض می‌کردند: با رفرش صفحه همه‌چیز پاک می‌شد. حالا هر سه به همین
اندپوینت می‌زنند و رکورد در ``Favorite`` می‌نشیند، که پنل کاربری هم از
همان می‌خواند.

برای مهمان ۴۰۱ برمی‌گردد نه ریدایرکت: ``fetch`` ریدایرکت را دنبال
می‌کند و به‌جای JSON یک صفحه‌ی HTML می‌گیرد، و کلاینت فکر می‌کند ذخیره
شده. پس نشانی ورود در خودِ پاسخ می‌آید تا صفحه خودش تصمیم بگیرد.
"""

import json

from django.conf import settings
from django.http import JsonResponse
from django.views import View

from apps.accounts.models import Favorite

from .models import Product


def favorite_ids(user):
    """شناسه‌ی محصول‌هایی که این کاربر نشان کرده — برای رنگ‌کردن قلب‌ها."""
    if not user.is_authenticated:
        return set()
    return set(Favorite.objects.filter(user=user).values_list('product_id', flat=True))


class FavoriteToggleView(View):
    """POST {product: <id>, on: <bool>} → {ok, on, count}"""

    def post(self, request):
        if not request.user.is_authenticated:
            return JsonResponse({
                'ok': False,
                'auth': False,
                'error': 'برای ذخیره‌ی علاقه‌مندی‌ها وارد شوید.',
                'login': f'{settings.LOGIN_URL}?next={request.META.get("HTTP_REFERER", "/")}',
            }, status=401)

        try:
            data = json.loads(request.body or '{}')
            product_id = int(data['product'])
        except (json.JSONDecodeError, KeyError, TypeError, ValueError):
            return JsonResponse({'ok': False, 'error': 'درخواست نامعتبر است.'}, status=400)

        # محصول باید واقعاً وجود داشته باشد و منتشر شده باشد، وگرنه
        # می‌شد با یک عدد دلخواه ردیف ساخت.
        if not Product.objects.live().filter(pk=product_id).exists():
            return JsonResponse({'ok': False, 'error': 'محصول پیدا نشد.'}, status=404)

        wanted = bool(data.get('on', True))
        if wanted:
            # get_or_create نه create: قید یکتا هست و دو کلیکِ پشت‌هم
            # نباید ۵۰۰ بدهد.
            Favorite.objects.get_or_create(user=request.user, product_id=product_id)
        else:
            Favorite.objects.filter(user=request.user, product_id=product_id).delete()

        return JsonResponse({
            'ok': True,
            'on': wanted,
            'count': Favorite.objects.filter(user=request.user).count(),
        })
