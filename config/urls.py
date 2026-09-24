"""
نقشه‌ی نشانی‌ها.

مسیرهای عمومی سایت بالا می‌آیند و پنل جنگو پایین‌تر، چون ریشه («/»)
صفحه‌ی اصلی است و باید اول بررسی شود.
"""

from django.conf import settings
from django.conf.urls.static import static
from django.contrib import admin
from django.contrib.sitemaps.views import sitemap
from django.urls import include, path
from django.views.decorators.cache import cache_page

from apps.pages import seo_views
from apps.pages.sitemaps import SITEMAPS

admin.site.site_header = 'رُزِت'
admin.site.site_title = 'رُزِت'
admin.site.index_title = 'مدیریت'

urlpatterns = [
    path('admin/', admin.site.urls),

    # فایل‌های فنیِ ریشه — خزنده‌ها و مرورگرها فقط همین‌جا دنبالشان
    # می‌گردند. apps/pages/seo_views.py
    path('robots.txt', seo_views.robots_txt, name='robots'),
    path('sitemap.xml', cache_page(60 * 60)(sitemap),
         {'sitemaps': SITEMAPS, 'template_name': 'seo/sitemap.xml'}, name='sitemap'),
    path('site.webmanifest', seo_views.webmanifest, name='webmanifest'),
    path('favicon.ico', seo_views.FaviconView.as_view()),

    # تصاویر خصوصی کیک اختصاصی — فقط با بررسی دسترسی سرو می‌شوند.
    path('', include('apps.custom_cake.urls')),

    path('', include('apps.catalog.urls')),
    path('', include('apps.accounts.urls')),
    path('', include('apps.orders.urls')),
    # پنل کارکنان — تابلوی سفارش‌ها. ورودش (staff/login/) در accounts است.
    path('', include('apps.staffpanel.urls')),

    # صفحه‌های عمومی. آخر می‌آید چون الگوی '' همه‌چیز را می‌گیرد.
    path('', include('apps.pages.urls')),
]

# صفحه‌های خطا — apps/pages/errors.py. جنگو فقط وقتی DEBUG خاموش است
# سراغشان می‌رود.
handler404 = 'apps.pages.errors.not_found'
handler500 = 'apps.pages.errors.server_error'

if settings.DEBUG:
    from apps.pages import errors

    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
    # پیش‌نمایش صفحه‌های خطا در توسعه؛ با DEBUG=True جنگو صفحه‌ی دیباگ
    # را نشان می‌دهد و این دو هیچ‌وقت دیده نمی‌شدند.
    urlpatterns += [
        path('_errors/404/', errors.not_found),
        path('_errors/500/', errors.server_error),
    ]
