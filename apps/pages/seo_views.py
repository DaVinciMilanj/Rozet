"""
فایل‌های فنیِ ریشه‌ی سایت: robots.txt، manifest و favicon.ico.

هر سه باید درست در ریشه باشند — خزنده‌ها و مرورگرها همان‌جا دنبالشان
می‌گردند، نه زیر /static/. نبودنشان هم فقط یک ۴۰۴ نیست: هر درخواستِ
favicon.ico صفحه‌ی ۴۰۴ کاملِ سایت را با چند کوئری دیتابیس می‌ساخت.
"""

from django.conf import settings
from django.http import HttpResponse, JsonResponse
from django.templatetags.static import static
from django.urls import reverse
from django.views.decorators.cache import cache_control
from django.views.decorators.http import require_GET
from django.views.generic import RedirectView

from apps.common.seo import DEFAULT_DESCRIPTION, SITE_NAME, SITE_NAME_EN, absolute

# مسیرهایی که در نتایج جست‌وجو معنایی ندارند: پنل‌ها، حساب و پرداخت،
# اندپوینت‌های JSON و تصاویر خصوصی. صفحه‌های حساب و پرداخت خودشان هم
# noindex دارند؛ اینجا جلوی هدررفتن بودجه‌ی خزش گرفته می‌شود.
DISALLOW = (
    '/admin/',
    '/staff/',
    '/account/',
    '/checkout/',
    '/auth/',
    '/logout/',
    '/private/',
    '/_errors/',
    '/cart/',
    '/favorite/',
    '/review/',
    '/*/api/',
    # فهرست محصولات با مرتب‌سازی، نما، بازه‌ی قیمت یا ویژگی همان صفحه است
    # و canonical هم به نسخه‌ی بی‌پارامتر اشاره می‌کند. دسته (cat) و
    # مناسبت (occ) صفحه‌ی فرود خودشان‌اند و می‌مانند.
    '/*?*sort=',
    '/*?*view=',
    '/*?*min=',
    '/*?*max=',
    '/*?*feat=',
)


@require_GET
@cache_control(max_age=60 * 60 * 24, public=True)
def robots_txt(request):
    if not settings.SEO_INDEXING:
        # سرور آزمایشی: هیچ‌چیز ایندکس نشود.
        lines = ['User-agent: *', 'Disallow: /']
    else:
        lines = ['User-agent: *', 'Allow: /']
        lines += [f'Disallow: {path}' for path in DISALLOW]
        lines += ['', f'Sitemap: {absolute(request, reverse("sitemap"))}']
    return HttpResponse('\n'.join(lines) + '\n', content_type='text/plain; charset=utf-8')


@require_GET
@cache_control(max_age=60 * 60 * 24 * 7, public=True)
def webmanifest(request):
    """
    مانیفست وب — «افزودن به صفحه‌ی اصلی» در موبایل، و آیکن و رنگ نوار
    مرورگر اندروید.
    """
    return JsonResponse({
        'name': f'{SITE_NAME} — کافه‌قنادی',
        'short_name': SITE_NAME,
        'description': DEFAULT_DESCRIPTION,
        'lang': 'fa-IR',
        'dir': 'rtl',
        'start_url': reverse('pages:home'),
        'scope': '/',
        'display': 'standalone',
        'background_color': '#17120F',
        'theme_color': '#17120F',
        'icons': [
            {'src': static('assets/logo/icon-192.png'), 'sizes': '192x192',
             'type': 'image/png', 'purpose': 'any'},
            {'src': static('assets/logo/icon-512.png'), 'sizes': '512x512',
             'type': 'image/png', 'purpose': 'any'},
            {'src': static('assets/logo/icon-maskable-512.png'), 'sizes': '512x512',
             'type': 'image/png', 'purpose': 'maskable'},
        ],
        'categories': ['food', 'shopping'],
        'id': SITE_NAME_EN.lower(),
    }, content_type='application/manifest+json',
        json_dumps_params={'ensure_ascii': False})


class FaviconView(RedirectView):
    """/favicon.ico ← آیکن واقعی زیر static، با ریدایرکت دائمی."""

    permanent = True

    def get_redirect_url(self, *args, **kwargs):
        return static('assets/logo/favicon-32.png')
