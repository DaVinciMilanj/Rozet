"""
سئو — متا، canonical، Open Graph و داده‌ی ساختاریافته (JSON-LD).

هر صفحه یک دیکشنری ``seo`` می‌گیرد و ``templates/_seo_head.html`` همه‌ی
تگ‌های head را از روی همان می‌سازد. صفحه‌ای که چیزی نگوید، مقدار پیش‌فرض
را از context processor می‌گیرد؛ پس هیچ صفحه‌ای بی عنوان و بی canonical
نمی‌ماند.

**نشانی مطلق.** canonical، og:image، sitemap و JSON-LD باید نشانی کامل
باشند. منبعش ``settings.SITE_URL`` است؛ تا دامنه تعیین نشده خالی است و
نشانی از خودِ درخواست ساخته می‌شود. با پرشدنش همه‌جا یکجا عوض می‌شود.

**قیمت در schema.** گوگل واحد پول را کد ISO می‌خواهد. «تومان» کد ندارد،
پس قیمت با ``IRR`` و به ریال گزارش می‌شود — همان عددی که در دیتابیس است.
"""

from datetime import timedelta
from urllib.parse import urlencode

from django.conf import settings
from django.templatetags.static import static
from django.urls import reverse
from django.utils import timezone


SITE_NAME = 'رُزِت'
SITE_NAME_EN = 'ROZET'
DEFAULT_TITLE = 'رُزِت | کافه‌قنادی، کیک تولد و شیرینی دست‌ساز در مشهد'
DEFAULT_DESCRIPTION = (
    'کافه‌قنادی رُزِت در مشهد، بلوار قرنی: کیک تولد، کیک اختصاصی با طرح دلخواه، '
    'شیرینی تر و دسر دست‌ساز با پخت روز. سفارش آنلاین، تحویل حضوری و ارسال در شهر.')
DEFAULT_IMAGE = 'assets/images/brand-story.webp'
LOGO = 'assets/logo/rozet-icon.webp'

ROBOTS_INDEX = 'index, follow, max-image-preview:large, max-snippet:-1, max-video-preview:-1'
ROBOTS_NOINDEX = 'noindex, follow'
ROBOTS_PRIVATE = 'noindex, nofollow'

SCHEMA = 'https://schema.org'
TITLE_MAX = 60
DESCRIPTION_MAX = 160


# ═══════════════════════════════════════════════════════════════════
#  نشانی
# ═══════════════════════════════════════════════════════════════════

def site_url(request=None):
    """ریشه‌ی سایت بدون / پایانی: از تنظیمات، یا از خودِ درخواست."""
    if settings.SITE_URL:
        return settings.SITE_URL
    if request is None:
        return ''
    return f'{request.scheme}://{request.get_host()}'


def absolute(request, url):
    """نشانی نسبی (مثل خروجی static یا reverse) ← نشانی کامل."""
    if not url:
        return ''
    if url.startswith(('http://', 'https://', '//')):
        return url
    return site_url(request) + (url if url.startswith('/') else '/' + url)


def canonical(request, keep=()):
    """
    نشانی رسمی صفحه: مسیر، به‌علاوه‌ی فقط پارامترهایی که واقعاً صفحه‌ی
    دیگری می‌سازند (``keep``).

    بقیه‌ی پارامترها — مرتب‌سازی، بازه‌ی قیمت، utm تبلیغات، شناسه‌ی
    کلیک — همان محتوا را نشان می‌دهند و اگر در canonical بمانند، گوگل
    هر ترکیبشان را یک صفحه‌ی تکراری می‌شمارد.
    """
    params = [(key, request.GET[key]) for key in keep if request.GET.get(key)]
    query = f'?{urlencode(params)}' if params else ''
    return absolute(request, request.path) + query


# ═══════════════════════════════════════════════════════════════════
#  متن
# ═══════════════════════════════════════════════════════════════════

def clip(text, limit):
    """کوتاه‌کردن روی مرز کلمه — گوگل وسطِ کلمه بریدن را بد نشان می‌دهد."""
    text = ' '.join(str(text or '').split())
    if len(text) <= limit:
        return text
    cut = text[:limit - 1].rsplit(' ', 1)[0].rstrip('،,.؛:-— ')
    return cut + '…'


def fit_title(*candidates):
    """
    اولین عنوانی که در ۶۰ نویسه جا شود — از کامل‌ترین به کوتاه‌ترین.

    نام محصول و دسته طول ثابتی ندارند؛ به‌جای بریدن وسط عبارت، نسخه‌ی
    کوتاه‌ترِ از پیش نوشته‌شده جایگزین می‌شود.
    """
    for candidate in candidates:
        candidate = ' '.join(str(candidate or '').split())
        if candidate and len(candidate) <= TITLE_MAX:
            return candidate
    return clip(candidates[-1], TITLE_MAX)


def page_title(name):
    """«نام | رُزِت» — مگر اینکه نام خودش برند را داشته باشد."""
    name = ' '.join(str(name or '').split())
    if not name:
        return DEFAULT_TITLE
    if SITE_NAME in name:
        return clip(name, TITLE_MAX)
    return clip(f'{name} | {SITE_NAME}', TITLE_MAX)


# ═══════════════════════════════════════════════════════════════════
#  دیکشنری صفحه
# ═══════════════════════════════════════════════════════════════════

def build(request, *, title=None, description=None, image=None, image_alt=None,
          kind='website', robots=None, keep=(), jsonld=(), extra=()):
    """
    همه‌ی آنچه ``_seo_head.html`` لازم دارد.

    ``title`` کامل است («… | رُزِت»)؛ برای ساختنش ``page_title`` هست.
    ``extra`` جفت‌های (property, content) برای متاهای اضافه‌ی Open Graph
    است، مثل قیمت محصول.
    """
    indexable = settings.SEO_INDEXING
    return {
        'title': title or DEFAULT_TITLE,
        'description': clip(description or DEFAULT_DESCRIPTION, DESCRIPTION_MAX),
        'canonical': canonical(request, keep),
        'robots': (robots or ROBOTS_INDEX) if indexable else ROBOTS_PRIVATE,
        'type': kind,
        'image': absolute(request, image or static(DEFAULT_IMAGE)),
        'image_alt': image_alt or title or DEFAULT_TITLE,
        'extra': list(extra),
        'jsonld': [block for block in jsonld if block],
    }


# ═══════════════════════════════════════════════════════════════════
#  داده‌ی ساختاریافته
# ═══════════════════════════════════════════════════════════════════

def _id(request, anchor):
    return f'{site_url(request)}/#{anchor}'


def bakery(request):
    """
    خودِ کافه — Bakery (زیرگونه‌ی LocalBusiness).

    این همان است که در جست‌وجوی «قنادی در مشهد» و روی نقشه‌ی گوگل
    نشانی، ساعت کار و تلفن را کنار نام نشان می‌دهد. فیلدهای خالیِ
    تنظیمات (تلفن، مختصات، شبکه‌های اجتماعی) اصلاً نوشته نمی‌شوند؛
    مقدار خالی در schema خطای اعتبارسنجی است.
    """
    cafe = settings.CAFE
    home = site_url(request) + '/'
    data = {
        '@context': SCHEMA,
        '@type': 'Bakery',
        '@id': _id(request, 'bakery'),
        'name': cafe['name'],
        'alternateName': SITE_NAME_EN,
        'url': home,
        'logo': absolute(request, static(LOGO)),
        'image': absolute(request, static(DEFAULT_IMAGE)),
        'description': DEFAULT_DESCRIPTION,
        'servesCuisine': ['کیک', 'شیرینی', 'دسر'],
        'priceRange': '$$',
        'currenciesAccepted': 'IRR',
        'address': {
            '@type': 'PostalAddress',
            'streetAddress': cafe['address'],
            'addressLocality': cafe['city'],
            'addressRegion': cafe['province'],
            'addressCountry': 'IR',
        },
        'openingHoursSpecification': [{
            '@type': 'OpeningHoursSpecification',
            'dayOfWeek': list(days),
            'opens': opens,
            'closes': closes,
        } for _label, days, opens, closes in settings.OPENING_HOURS],
        'hasMap': ('https://www.google.com/maps/search/?api=1&query='
                   + (f"{cafe['latitude']},{cafe['longitude']}"
                      if cafe.get('latitude') and cafe.get('longitude')
                      else f"{cafe['city']} {cafe['address']}").replace(' ', '+')),
    }
    if cafe.get('postal_code'):
        data['address']['postalCode'] = cafe['postal_code']
    if cafe.get('landline'):
        data['telephone'] = cafe['landline']
    if cafe.get('latitude') and cafe.get('longitude'):
        data['geo'] = {'@type': 'GeoCoordinates',
                       'latitude': cafe['latitude'], 'longitude': cafe['longitude']}
    same_as = [cafe[key] for key in ('instagram', 'telegram', 'whatsapp') if cafe.get(key)]
    if same_as:
        data['sameAs'] = same_as
    return data


def website(request):
    """
    WebSite با SearchAction — کادر جست‌وجوی سایت زیر نتیجه‌ی گوگل.

    هدف جست‌وجو همان پارامتر ``q`` صفحه‌ی محصولات است که
    ``product-list.js`` از نشانی می‌خواند.
    """
    return {
        '@context': SCHEMA,
        '@type': 'WebSite',
        '@id': _id(request, 'website'),
        'url': site_url(request) + '/',
        'name': SITE_NAME,
        'alternateName': SITE_NAME_EN,
        'inLanguage': 'fa-IR',
        'publisher': {'@id': _id(request, 'bakery')},
        'potentialAction': {
            '@type': 'SearchAction',
            'target': {
                '@type': 'EntryPoint',
                'urlTemplate': absolute(request, reverse('catalog:product_list'))
                               + '?q={search_term_string}',
            },
            'query-input': 'required name=search_term_string',
        },
    }


def breadcrumbs(request, trail):
    """``trail`` فهرست (نام، نشانی) از خانه تا خودِ صفحه."""
    return {
        '@context': SCHEMA,
        '@type': 'BreadcrumbList',
        'itemListElement': [{
            '@type': 'ListItem',
            'position': index,
            'name': name,
            'item': absolute(request, url),
        } for index, (name, url) in enumerate(trail, start=1)],
    }


def home_trail():
    return [('خانه', reverse('pages:home'))]


def product(request, item, category_name='', reviews=()):
    """
    Product با Offer، امتیاز و نظرها — ستاره و قیمت زیر نتیجه‌ی گوگل.

    ``aggregateRating`` فقط وقتی نوشته می‌شود که نظرِ تأییدشده باشد؛
    امتیازِ صفر از صفر نظر در گوگل «داده‌ی نادرست» حساب می‌شود.
    """
    url = absolute(request, item.get_absolute_url())
    images = [absolute(request, image.image.url) for image in item.images.all()]
    data = {
        '@context': SCHEMA,
        '@type': 'Product',
        '@id': f'{url}#product',
        'name': item.name,
        'url': url,
        'sku': f'RZ-{item.pk}',
        'description': clip(item.description or item.short_description or item.name, 5000),
        'image': images or [absolute(request, static(DEFAULT_IMAGE))],
        'brand': {'@type': 'Brand', 'name': SITE_NAME},
        'offers': {
            '@type': 'Offer',
            'url': url,
            'priceCurrency': 'IRR',
            'price': item.price_rial,
            'priceValidUntil': (timezone.localdate() + timedelta(days=30)).isoformat(),
            'availability': f'{SCHEMA}/{"InStock" if item.in_stock else "OutOfStock"}',
            'itemCondition': f'{SCHEMA}/NewCondition',
            'seller': {'@id': _id(request, 'bakery')},
            # شیرینی و کیک فاسدشدنی است؛ مرجوعی ندارد. گفتنش صریح بهتر از
            # سکوت است — گوگل بدون آن هشدار «سیاست مرجوعی» می‌دهد.
            'hasMerchantReturnPolicy': {
                '@type': 'MerchantReturnPolicy',
                'applicableCountry': 'IR',
                'returnPolicyCategory': f'{SCHEMA}/MerchantReturnNotPermitted',
            },
        },
    }
    if category_name:
        data['category'] = category_name
    if item.name_en:
        data['alternateName'] = item.name_en
    if item.reviews_count:
        data['aggregateRating'] = {
            '@type': 'AggregateRating',
            'ratingValue': float(item.rating),
            'reviewCount': item.reviews_count,
            'bestRating': 5,
            'worstRating': 1,
        }
    if reviews:
        data['review'] = [{
            '@type': 'Review',
            'author': {'@type': 'Person', 'name': review.display_name},
            'datePublished': timezone.localtime(review.created_at).date().isoformat(),
            'reviewRating': {'@type': 'Rating', 'ratingValue': review.rating,
                             'bestRating': 5, 'worstRating': 1},
            **({'reviewBody': review.text} if review.text else {}),
        } for review in reviews]
    return data


def item_list(request, products, name=''):
    """فهرست محصولات صفحه‌ی مجموعه — گوگل از آن کاروسل می‌سازد."""
    return {
        '@context': SCHEMA,
        '@type': 'ItemList',
        **({'name': name} if name else {}),
        'numberOfItems': len(products),
        'itemListElement': [{
            '@type': 'ListItem',
            'position': index,
            'url': absolute(request, item['url']),
            'name': item['name'],
        } for index, item in enumerate(products, start=1)],
    }
