"""
نقشه‌ی سایت — /sitemap.xml

سه بخش:
    صفحه‌های ثابت   خانه، محصولات، کیک اختصاصی، درباره ما
    دسته‌ها          /products/?cat=… — هر دسته صفحه‌ی فرود خودش است
    محصولات         با تاریخ آخرین تغییر و تصویرها (Google Image Sitemap)

صفحه‌های خصوصی (حساب، پرداخت، ورود، پنل‌ها) عمداً نیستند. نقشه فقط
چیزی را معرفی می‌کند که باید در گوگل پیدا شود.

دامنه: اگر ``SITE_URL`` پر باشد همان، وگرنه میزبانِ خودِ درخواست — تا
نقشه‌ی سایت هیچ‌وقت نشانی دامنه‌ی دیگری را نداشته باشد.
"""

from urllib.parse import urlsplit

from django.conf import settings
from django.contrib.sitemaps import Sitemap
from django.urls import reverse

from apps.catalog.models import Category, Occasion, Product


class SiteSitemap(Sitemap):
    """پایه: دامنه و پروتکل از SITE_URL، اگر تعیین شده باشد."""

    def get_domain(self, site=None):
        if settings.SITE_URL:
            return urlsplit(settings.SITE_URL).netloc
        return super().get_domain(site)

    def get_protocol(self, protocol=None):
        if settings.SITE_URL:
            return urlsplit(settings.SITE_URL).scheme
        return super().get_protocol(protocol)

    def get_urls(self, page=1, site=None, protocol=None):
        """
        هر ردیف، اگر زیرکلاس ``images`` داشته باشد، تصویرهایش را هم با
        نشانی مطلق می‌گیرد — قالب نقشه آن‌ها را به‌صورت <image:image>
        می‌نویسد.
        """
        base = f'{self.get_protocol(protocol)}://{self.get_domain(site)}'
        urls = super().get_urls(page, site, protocol)
        if hasattr(self, 'images'):
            for url in urls:
                url['images'] = [{**image, 'loc': base + image['loc']}
                                 if image['loc'].startswith('/') else image
                                 for image in self.images(url['item'])]
        return urls


class StaticSitemap(SiteSitemap):
    # (نام نشانی، اولویت، بسامد تغییر)
    PAGES = (
        ('pages:home', 1.0, 'daily'),
        ('catalog:product_list', 0.9, 'daily'),
        ('custom_cake:wizard', 0.8, 'monthly'),
        ('pages:about', 0.6, 'monthly'),
    )

    def items(self):
        return self.PAGES

    def location(self, item):
        return reverse(item[0])

    def priority(self, item):
        return item[1]

    def changefreq(self, item):
        return item[2]


class CategorySitemap(SiteSitemap):
    changefreq = 'weekly'
    priority = 0.8

    def items(self):
        # فقط دسته‌های سطح اول: فیلتر صفحه‌ی محصولات با همین‌ها کار می‌کند.
        return Category.objects.active().filter(parent__isnull=True).order_by('sort_order', 'name')


class OccasionSitemap(SiteSitemap):
    """«کیک تولد»، «کیک سالگرد»… — هر مناسبت یک صفحه‌ی فرود."""

    changefreq = 'weekly'
    priority = 0.7

    def items(self):
        return Occasion.objects.active().order_by('sort_order', 'name')

    def location(self, item):
        return f"{reverse('catalog:product_list')}?occ={item.slug}"


class ProductSitemap(SiteSitemap):
    changefreq = 'weekly'
    priority = 0.7

    def items(self):
        return Product.objects.live().prefetch_related('images').order_by('-updated_at')

    def lastmod(self, item):
        return item.updated_at

    def images(self, item):
        """تصویرهای محصول، با نشانی مطلق — برای جست‌وجوی تصویری گوگل."""
        return [{'loc': image.image.url, 'title': item.name}
                for image in item.images.all()]


SITEMAPS = {
    'static': StaticSitemap,
    'categories': CategorySitemap,
    'occasions': OccasionSitemap,
    'products': ProductSitemap,
}
