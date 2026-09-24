"""
صفحه‌های ویترین.
"""

from django.conf import settings
from django.db.models import Case, IntegerField, When
from django.urls import reverse
from django.utils import timezone
from django.views.generic import DetailView, TemplateView

from apps.common import seo
from apps.common.dates import jalali_date
from apps.common.money import format_toman, rial_to_toman
from apps.common.text import to_persian_digits

from .favorites import favorite_ids
from .models import Category, Occasion, Product, ProductFeature


# همان PAGE_SIZE در product-list.js: چند کارت در بار اول دیده می‌شود.
LIST_PAGE_SIZE = 8


def root_slugs():
    """
    نگاشت «شناسه‌ی دسته → اسلاگ ریشه‌اش»، با یک کوئری.

    محصول می‌تواند زیر یک زیردسته بنشیند («ماکارون» زیر «شیرینی تر»)،
    ولی فیلتر صفحه‌ی فهرست با دسته‌های سطح اول کار می‌کند. پس آنچه به
    کلاینت می‌رود ریشه است، نه خودِ دسته.

    نسخه‌ی قبلی روی ``category.parent`` بالا می‌رفت. با
    ``select_related('category__parent')`` تا دو سطح مشکلی نبود، ولی
    سطح سوم برای **هر محصول** یک کوئری می‌زد — اندازه‌گیری روی ۱۲
    محصولِ دو سطح تودرتو، ۱۲ کوئری اضافه نشان داد.

    کل درخت دسته چند ردیف بیشتر نیست، پس یک‌بار خوانده می‌شود و
    پیمایش در پایتون انجام می‌گیرد: مستقل از عمق، و همیشه یک کوئری.
    """
    rows = {}
    slugs = {}
    for pk, slug, parent_id in Category.objects.values_list('pk', 'slug', 'parent_id'):
        rows[pk] = parent_id
        slugs[pk] = slug

    resolved = {}

    def root_of(pk):
        if pk in resolved:
            return resolved[pk]
        seen = []
        current = pk
        # حلقه‌ی seen هم مراقب داده‌ی خرابِ حلقه‌دار است؛ بدون آن یک
        # دسته‌ی پدرِ خودش کل صفحه را قفل می‌کرد.
        while rows.get(current) is not None and current not in seen:
            seen.append(current)
            current = rows[current]
        for node in seen:
            resolved[node] = slugs.get(current, '')
        resolved[pk] = slugs.get(current, '')
        return resolved[pk]

    return {pk: root_of(pk) for pk in slugs}


class ProductListView(TemplateView):
    """
    فهرست محصولات.

    صفحه در تمپلیت یک اپ کامل سمت کلاینت است: فیلتر، مرتب‌سازی،
    صفحه‌بندی، اسلایدر قیمت، نمای سریع و همگام‌سازی با کوئری‌استرینگ —
    همه در جاوااسکریپت. بازنویسی‌شان سمت سرور یعنی از دست دادن همه‌ی
    آن تعامل، و شکستن ۱۰۶۶ خط CSS که برای همان DOM نوشته شده.

    پس فقط **منبع داده** عوض می‌شود: چهار آرایه‌ی ثابت بالای فایل JS
    جایشان را به یک ``json_script`` می‌دهند که از دیتابیس پر می‌شود.
    بقیه‌ی فایل دست‌نخورده است.

    آدرس‌های فیلتر (``?cat=…&sort=…``) همان قرارداد قبلی را دارند، پس
    لینک‌های ذخیره‌شده و دکمه‌ی back مرورگر کار می‌کنند.
    """

    template_name = 'catalog/product_list.html'

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)

        products = (Product.objects
                    .live()
                    .select_related('category')
                    .prefetch_related('images', 'occasions', 'features'))

        roots = root_slugs()
        payload = []
        for product in products:
            cover = product.cover
            payload.append({
                'id': product.pk,
                'name': product.name,
                'en': product.name_en,
                'url': product.get_absolute_url(),
                # جاوااسکریپت با تومان کار می‌کند (اسلایدر قیمت، نمایش،
                # سبد). تبدیل همین‌جا انجام می‌شود و یک‌بار.
                'price': rial_to_toman(product.price_rial),
                'cat': roots.get(product.category_id, ''),
                'img': cover.image.url if cover else '',
                'notes': product.short_description,
                'serves': product.serves,
                'badge': product.get_badge_display() if product.badge else '',
                'occ': [o.slug for o in product.occasions.all()],
                'feat': [f.slug for f in product.features.all()],
                'pop': product.sales_count,
                # مبنای مرتب‌سازی «تازه‌ترین». عدد بزرگ‌تر = تازه‌تر.
                'added': int(product.created_at.timestamp()),
                'stock': product.in_stock,
            })

        def options(queryset):
            return [{'id': row.slug, 'label': row.name} for row in queryset]

        context['catalog_data'] = {
            'products': payload,
            # فقط دسته‌های سطح اول؛ زیردسته‌ها در فیلتر این صفحه نمی‌آیند.
            'categories': options(Category.objects.active().filter(parent__isnull=True)),
            'occasions': options(Occasion.objects.active()),
            'features': options(ProductFeature.objects.active()),
            # قلب‌ها را جاوااسکریپت می‌کشد، پس فهرست نشان‌شده‌ها باید
            # همراه داده برود نه در مارکاپ.
            'favorites': sorted(favorite_ids(self.request.user)),
        }
        context['seo'], context['list_heading'], context['list_lede'] = self._seo(payload)
        context['list_cards'], context['list_total'] = self._first_page(payload)
        context['cat_labels'] = {row['id']: row['label']
                                 for row in context['catalog_data']['categories']}
        context['favorite_set'] = set(context['catalog_data']['favorites'])
        return context

    def _first_page(self, payload):
        """
        صفحه‌ی اول کارت‌ها برای خودِ HTML — همان فیلتر دسته/مناسبت و همان
        ترتیب «محبوب‌ترین» که product-list.js اول نشان می‌دهد، تا بعد از
        اجرای جاوااسکریپت چیزی جابه‌جا نشود. خزنده بدون اجرای JS هم نام
        و پیوند محصولات را می‌بیند.
        """
        cats = [c for c in self.request.GET.get('cat', '').split(',') if c]
        occs = [o for o in self.request.GET.get('occ', '').split(',') if o]
        items = [row for row in payload
                 if (not cats or row['cat'] in cats)
                 and (not occs or any(o in row['occ'] for o in occs))]
        items.sort(key=lambda row: -row['pop'])
        return items[:LIST_PAGE_SIZE], len(items)

    def _single(self, key):
        """پارامتر تک‌مقداره؛ «cakes,pastries» ترکیب است، نه صفحه‌ی فرود."""
        value = self.request.GET.get(key, '').strip()
        return value if value and ',' not in value else ''

    def _seo(self, payload):
        """
        هر دسته و هر مناسبت صفحه‌ی فرود خودش است: «کیک» و «کیک تولد» را
        مردم جداگانه جست‌وجو می‌کنند، پس عنوان و توضیح و canonical جدا
        می‌گیرند. ترکیب فیلترها، مرتب‌سازی و بازه‌ی قیمت canonical را به
        همان صفحه برمی‌گردانند؛ نتیجه‌ی جست‌وجو (?q=) اصلاً ایندکس نمی‌شود.
        """
        request = self.request
        city = settings.CAFE['city']
        cat_slug, occ_slug = self._single('cat'), self._single('occ')
        category = (Category.objects.active().filter(slug=cat_slug, parent__isnull=True).first()
                    if cat_slug else None)
        occasion = Occasion.objects.active().filter(slug=occ_slug).first() if occ_slug else None

        items = payload
        if category:
            items = [row for row in items if row['cat'] == category.slug]
        if occasion:
            items = [row for row in items if occasion.slug in row['occ']]

        if category and occasion:
            heading = f'{category.name} {occasion.name}'
        elif category or occasion:
            heading = (category or occasion).name
        else:
            heading = 'همه‌ی کیک‌ها و شیرینی‌ها'

        count = to_persian_digits(len(items))
        tail = (f'{count} انتخاب با پخت روز و بدون مواد آماده، قیمت روشن و سفارش آنلاین '
                f'از کافه‌قنادی رُزِت؛ تحویل حضوری در {city} یا ارسال.')
        if category and category.description:
            lede = category.description
            description = f'{seo.clip(category.description, 90)} {tail}'
        elif category or occasion:
            lede = ''
            description = f'خرید {heading} دست‌ساز در {city}: {tail}'
        else:
            lede = ''
            description = (f'کیک تولد، کیک مراسم، شیرینی تر، دسر و شیرینی سنتی رُزِت در {city}، '
                           'همه با پخت روز. فیلتر بر اساس دسته، مناسبت و قیمت، و سفارش '
                           'آنلاین با تحویل حضوری یا ارسال.')

        list_url = reverse('catalog:product_list')
        trail = seo.home_trail() + [('محصولات', list_url)]
        keep = []
        if category:
            keep.append('cat')
            trail.append((category.name, f'{list_url}?cat={category.slug}'))
        if occasion:
            keep.append('occ')
            trail.append((occasion.name, seo.canonical(request, keep)))

        if category or occasion:
            title = seo.fit_title(
                f'خرید {heading} دست‌ساز در {city}؛ قیمت و سفارش آنلاین | {seo.SITE_NAME}',
                f'خرید {heading} دست‌ساز در {city} | {seo.SITE_NAME}',
                f'{heading} | {seo.SITE_NAME}')
        else:
            title = f'همه محصولات؛ کیک، شیرینی و دسر دست‌ساز در {city} | {seo.SITE_NAME}'
        return seo.build(
            request,
            title=title,
            description=description,
            image=items[0]['img'] if items and items[0]['img'] else None,
            robots=seo.ROBOTS_NOINDEX if request.GET.get('q') else None,
            keep=keep,
            jsonld=[seo.breadcrumbs(request, trail),
                    seo.item_list(request, items[:50], heading) if items else None]), heading, lede


class ProductDetailView(DetailView):
    """
    جزئیات محصول — /product/<slug>/

    مثل صفحه‌ی فهرست، موتور صفحه سمت کلاینت است (گالری، بزرگ‌نمایی،
    انتخاب اندازه و طعم و افزودنی، قیمت زنده، آکاردئون، هرم طعم، نظرها).
    پس فقط داده عوض می‌شود، نه مارکاپ و نه منطق.

    یک تفاوت با تمپلیت ساکن: آنجا محصول با ``?id=`` انتخاب می‌شد و کل
    آرایه در مرورگر بود. اینجا سرور از روی ``slug`` می‌داند کدام است و
    فقط همان یکی را می‌فرستد.
    """

    model = Product
    template_name = 'catalog/product_detail.html'
    context_object_name = 'product'

    def get_queryset(self):
        return (Product.objects
                .live()
                .select_related('category')
                .prefetch_related('images', 'flavor_notes', 'sizes',
                                  'flavors', 'addons'))

    def _product_payload(self, product, roots):
        images = list(product.images.all())
        cover = product.cover
        return {
            'id': product.pk,
            'name': product.name,
            'en': product.name_en,
            'url': product.get_absolute_url(),
            'price': rial_to_toman(product.price_rial),
            'cat': roots.get(product.category_id, ''),
            'img': cover.image.url if cover else '',
            # گالری سه‌تایی صفحه‌ی جزئیات. اگر فقط یک تصویر باشد، همان
            # یکی می‌آید و بندانگشتی‌ها خودشان کم می‌شوند.
            'gallery': [image.image.url for image in images],
            'notes': product.description or product.short_description,
            'serves': product.serves,
            'badge': product.get_badge_display() if product.badge else '',
            'rating': float(product.rating),
            'reviews': product.reviews_count,
            'stock': product.in_stock,
            'pyramid': [{'n': note.label, 'v': note.weight}
                        for note in product.flavor_notes.all()],
            'ingredients': product.ingredients,
            'allergen': product.allergens,
            'keep': product.keeping,
        }

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        product = self.object

        # محصولات مرتبط: هم‌دسته‌ها اول، بعد بقیه — همان ترتیب تمپلیت.
        # flavor_notes هم لازم است: _product_payload هرم طعم را برای
        # محصولات مرتبط هم می‌سازد و بدون این، هر کارتِ مرتبط یک کوئری
        # جدا می‌زد (اندازه‌گیری: ۸ کوئری اضافه).
        roots = root_slugs()
        root = roots.get(product.category_id, '')
        same_root = [pk for pk, slug in roots.items() if slug == root]
        # هم‌دسته‌ها باید از خودِ سرور اول بیایند: جاوااسکریپت فقط همین
        # هشت‌تا را مرتب می‌کند، و اگر هشت محصولِ تازه‌تر همه از دسته‌ی
        # دیگری بودند، هیچ هم‌دسته‌ای به صفحه نمی‌رسید.
        related = (Product.objects.in_stock()
                   .exclude(pk=product.pk)
                   .annotate(_other=Case(When(category_id__in=same_root, then=0),
                                         default=1, output_field=IntegerField()))
                   .order_by('_other', '-sales_count', '-created_at')
                   .select_related('category')
                   .prefetch_related('images', 'flavor_notes')[:8])
        reviews = list(product.reviews.filter(is_approved=True).select_related('user')[:20])
        categories = {row.slug: row.name for row in Category.objects.active()}

        context['product_data'] = {
            'product': self._product_payload(product, roots),
            'products': [self._product_payload(other, roots) for other in related],
            'categories': categories,
            'sizes': [{'id': str(size.pk), 'label': size.label,
                       'sub': size.serves, 'add': rial_to_toman(size.price_delta_rial)}
                      for size in product.sizes.all() if size.is_active],
            'flavors': [{'id': str(flavor.pk), 'label': flavor.label,
                         'add': rial_to_toman(flavor.price_delta_rial)}
                        for flavor in product.flavors.all() if flavor.is_active],
            'addons': [{'id': str(addon.pk), 'label': addon.label,
                        'price': rial_to_toman(addon.price_delta_rial)}
                       for addon in product.addons.all() if addon.is_active],
            # پیش‌فرض‌ها جدا می‌آیند تا ترتیب نمایش به‌هم نخورد: در تمپلیت
            # ترتیب کوچک/متوسط/بزرگ است ولی پیش‌فرض متوسط است.
            'defaults': {
                'size': next((str(x.pk) for x in product.sizes.all() if x.is_default),
                             next((str(x.pk) for x in product.sizes.all()), '')),
                'flavor': next((str(x.pk) for x in product.flavors.all() if x.is_default),
                               next((str(x.pk) for x in product.flavors.all()), '')),
            },
            'favorite': product.pk in favorite_ids(self.request.user),
            'reviews': [{'name': review.display_name,
                         'rating': review.rating,
                         # شمسی، هم‌شکل تاریخی که فرم برای نظر تازه می‌سازد
                         'date': jalali_date(timezone.localtime(review.created_at)),
                         'text': review.text}
                        for review in reviews],
        }
        # نسخه‌ی سرورِ بخش‌هایی که جاوااسکریپت می‌سازد — تا خزنده مشخصات،
        # نظرها و پیوند محصولات مرتبط را در خودِ HTML ببیند.
        context['related_cards'] = context['product_data']['products'][:4]
        context['reviews'] = reviews
        context['category_name'] = categories.get(root, '')
        context['root_slug'] = root
        context['seo'] = self._seo(product, categories.get(root, ''), root, reviews)
        return context

    def _seo(self, product, category_name, root, reviews):
        """
        عنوان، توضیح، Open Graph محصول و داده‌ی ساختاریافته‌ی Product.

        اگر مدیر در پنل «عنوان سئو» یا «توضیح سئو» نوشته باشد، همان
        می‌آید؛ وگرنه از روی خودِ محصول ساخته می‌شود.
        """
        request = self.request
        city = settings.CAFE['city']
        name, kind = product.name, category_name or 'شیرینی'
        # عنوان: نام محصول اول (کلیدواژه‌ی اصلی)، بعد نیتِ خرید و شهر —
        # «قیمت» و «خرید» همان کلمه‌هایی است که مردم کنار نام کیک می‌زنند.
        title = product.meta_title or seo.fit_title(
            f'{name} | قیمت و خرید {kind} در {city} | {seo.SITE_NAME}',
            f'{name} | خرید {kind} در {city} | {seo.SITE_NAME}',
            f'{name} | خرید آنلاین در {city} | {seo.SITE_NAME}',
            f'{name} | {seo.SITE_NAME}')
        # توضیح: چه هست، برای چند نفر، قیمت، موجودی و راه سفارش — همان
        # چیزهایی که زیر نتیجه‌ی گوگل تصمیم کلیک را می‌گیرند.
        summary = ((product.short_description or product.description or '')
                   .replace(' · ', '، ').strip().rstrip('.،؛ '))
        stock = 'موجود با پخت روز' if product.in_stock else 'فعلاً ناموجود'
        bits = [f'{name}: {summary}.' if summary else f'{name} دست‌ساز رُزِت.']
        if product.serves:
            bits.append(f'{product.serves}،')
        bits.append(f'قیمت {format_toman(product.price_rial)} تومان، {stock}.')
        bits.append(f'سفارش آنلاین از رُزِت با تحویل حضوری یا ارسال در {city}.')
        description = product.meta_description or ' '.join(bits)
        cover = product.cover
        products_url = reverse('catalog:product_list')
        trail = seo.home_trail() + [('محصولات', products_url)]
        if category_name:
            trail.append((category_name, f'{products_url}?cat={root}'))
        trail.append((product.name, product.get_absolute_url()))
        return seo.build(
            request,
            title=title,
            description=description,
            image=cover.image.url if cover else None,
            image_alt=(cover.alt if cover and cover.alt else product.name),
            kind='product',
            extra=[
                ('product:price:amount', str(product.price_rial)),
                ('product:price:currency', 'IRR'),
                ('product:availability', 'in stock' if product.in_stock else 'out of stock'),
                ('product:brand', seo.SITE_NAME),
            ],
            jsonld=[seo.product(request, product, category_name, reviews[:5]),
                    seo.breadcrumbs(request, trail)])
