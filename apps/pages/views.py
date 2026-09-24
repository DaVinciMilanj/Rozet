"""
صفحه‌های عمومی سایت.
"""

from django.conf import settings
from django.db.models import Q
from django.templatetags.static import static
from django.urls import reverse
from django.views.generic import TemplateView

from apps.catalog.favorites import favorite_ids
from apps.catalog.models import Category, GalleryImage, Product
from apps.common import seo


def _cards(queryset, limit):
    """
    کوئری آماده برای گرید کارت محصول.

    کارت به دسته، تصویر کاور و نت‌های طعم نیاز دارد. بدون این سه، شش
    کارت می‌شود نوزده کوئری.
    """
    return (queryset
            .select_related('category')
            .prefetch_related('images', 'flavor_notes')
            .order_by('-sales_count', '-created_at')[:limit])


class HomeView(TemplateView):
    """
    صفحه‌ی اصلی.

    مارکاپ دقیقاً همان تمپلیت است؛ فقط به‌جای کارت‌های دستی روی کوئری‌ست
    حلقه می‌زند. هر بخش بدون داده خالی می‌ماند و صفحه نمی‌شکند —
    دیتابیس هنوز خالی است و باید همان‌طور هم بالا بیاید.
    """

    template_name = 'pages/index.html'

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        home = settings.HOME_SECTIONS
        pastries = home['pastries']

        context['cakes'] = _cards(
            Product.objects.in_stock().filter(category__slug=home['cakes']),
            home['cakes_count'])

        # شیرینی تر: هم خودِ دسته و هم زیردسته‌هایش (ماکارون، تارت، …).
        context['pastries'] = _cards(
            Product.objects.in_stock().filter(
                Q(category__slug=pastries) | Q(category__parent__slug=pastries)),
            home['pastries_count'])

        # تراشه‌های فیلتر از زیردسته‌های واقعی ساخته می‌شوند، نه از فهرست
        # ثابت در HTML — اگر مدیر زیردسته‌ای اضافه کند، خودش می‌آید.
        context['pastry_filters'] = (Category.objects.active()
                                     .filter(parent__slug=pastries)
                                     .order_by('sort_order', 'name'))

        context['gallery'] = GalleryImage.objects.active()[:5]
        # یک کوئری برای همه‌ی کارت‌ها؛ قالب کارت از همین می‌خواند که
        # قلب را پر بکشد یا خالی.
        context['favorite_ids'] = favorite_ids(self.request.user)
        # صفحه‌ی اصلی معرف خودِ کسب‌وکار است: WebSite (با کادر جست‌وجوی
        # گوگل) و Bakery (نشانی، ساعت کار، نقشه) همین‌جا می‌نشینند.
        context['seo'] = seo.build(
            self.request, jsonld=[seo.website(self.request), seo.bakery(self.request)])
        return context


class AboutView(TemplateView):
    """
    درباره ما — /about/

    صفحه‌ی متنی است و از دیتابیس چیزی نمی‌خواهد؛ تنها داده‌ای که دارد
    نشانی و تلفن و ساعت کار است که از ``settings.CAFE`` می‌آید و
    context_processor سایت آن را به هر صفحه می‌دهد.

    کارت‌های تماس شرطی‌اند: تلفن و اینستاگرامی که در تنظیمات خالی است
    اصلاً نمایش داده نمی‌شود. کارتِ تلفنی که زنگ نمی‌خورد بدتر از
    نبودنش است.
    """

    template_name = 'pages/about.html'

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        request = self.request
        city = settings.CAFE['city']
        context['seo'] = seo.build(
            request,
            title=f'درباره ما، نشانی و ساعت کار کافه‌قنادی در {city} | {seo.SITE_NAME}',
            description=(f'داستان کافه‌قنادی رُزِت در {city}، معیارهای پخت روزانه با مواد '
                         f'درجه‌یک، نشانی {settings.CAFE["address"]} و مسیر روی نقشه، ساعت کار '
                         'و راه‌های تماس برای سفارش کیک و شیرینی.'),
            image=static('assets/images/rozet-shop.jpg'),
            image_alt=f'کافه‌قنادی رُزِت در {city}',
            jsonld=[
                seo.bakery(request),
                seo.breadcrumbs(request, seo.home_trail() + [
                    ('درباره ما', reverse('pages:about'))]),
            ])
        return context
