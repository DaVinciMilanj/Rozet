"""
تنظیمات پروژه‌ی رُزِت.

هر چیزی که بین توسعه و تولید فرق می‌کند از متغیر محیطی خوانده می‌شود؛
مقدار پیش‌فرضش امنِ توسعه است. فایل .env کنار manage.py گذاشته می‌شود و
هیچ‌وقت به مخزن نمی‌رود.
"""

from pathlib import Path

from decouple import AutoConfig, Csv
from django.core.management.utils import get_random_secret_key

BASE_DIR = Path(__file__).resolve().parent.parent

# AutoConfig از BASE_DIR به بالا دنبال .env می‌گردد و اگر پیدا نکرد به
# متغیرهای محیطی سیستم برمی‌گردد — پس روی سرور بدون فایل .env هم کار
# می‌کند. cast تبدیل را همین‌جا انجام می‌دهد: bool و Csv و int لازم
# نیست دستی نوشته شوند.
config = AutoConfig(search_path=BASE_DIR)


# ─────────────────────────────────────────────────────────────────────
#  پایه
# ─────────────────────────────────────────────────────────────────────

# پیش‌فرض خاموش. اگر روی سرور کسی یادش برود DEBUG را تعریف کند، سایت
# نباید با صفحه‌ی دیباگ — که تنظیمات و ردِ خطا را به هر بازدیدکننده‌ای
# نشان می‌دهد — بالا بیاید. در توسعه .env آن را روشن می‌کند.
DEBUG = config('DEBUG', default=False, cast=bool)

# در تولید SECRET_KEY باید از محیط بیاید. اگر نیامد و DEBUG خاموش است،
# بالا نیامدن بهتر از اجرا با کلید تصادفیِ هر بار متفاوت است — کلید
# تصادفی یعنی همه‌ی نشست‌ها با هر ریستارت باطل می‌شوند.
SECRET_KEY = config('SECRET_KEY', default='')
if not SECRET_KEY:
    if DEBUG:
        SECRET_KEY = 'django-insecure-' + get_random_secret_key()
    else:
        raise RuntimeError('SECRET_KEY باید در محیط تعریف شود.')

ALLOWED_HOSTS = config('ALLOWED_HOSTS',
                       default='localhost,127.0.0.1,[::1]', cast=Csv())

# فرم‌های POST از دامنه‌ی اصلی می‌آیند؛ پشت HTTPS باید scheme هم بیاید.
CSRF_TRUSTED_ORIGINS = config('CSRF_TRUSTED_ORIGINS', default='', cast=Csv())

# تعداد پروکسی‌های خودمان جلوی جنگو (معمولاً ۱: nginx). فقط با عدد
# درست، IP واقعی کاربر از X-Forwarded-For خوانده می‌شود؛ با صفر (حالت
# توسعه) همان REMOTE_ADDR. apps/common/http.py
TRUSTED_PROXY_COUNT = config('TRUSTED_PROXY_COUNT', default=0, cast=int)

ROOT_URLCONF = 'config.urls'
WSGI_APPLICATION = 'config.wsgi.application'
ASGI_APPLICATION = 'config.asgi.application'

DEFAULT_AUTO_FIELD = 'django.db.models.BigAutoField'


# ─────────────────────────────────────────────────────────────────────
#  اپ‌ها
# ─────────────────────────────────────────────────────────────────────

DJANGO_APPS = [
    'django.contrib.admin',
    'django.contrib.auth',
    'django.contrib.contenttypes',
    'django.contrib.sessions',
    'django.contrib.messages',
    'django.contrib.humanize',
    'django.contrib.sitemaps',
    'django.contrib.staticfiles',
]

LOCAL_APPS = [
    'apps.common',
    'apps.accounts',
    'apps.catalog',
    'apps.orders',
    'apps.custom_cake',
    'apps.payments',
    'apps.staffpanel',
    'apps.pages',
]

INSTALLED_APPS = DJANGO_APPS + LOCAL_APPS


MIDDLEWARE = [
    'django.middleware.security.SecurityMiddleware',
    'django.contrib.sessions.middleware.SessionMiddleware',
    'django.middleware.locale.LocaleMiddleware',
    'django.middleware.common.CommonMiddleware',
    'django.middleware.csrf.CsrfViewMiddleware',
    'django.contrib.auth.middleware.AuthenticationMiddleware',
    'django.contrib.messages.middleware.MessageMiddleware',
    'django.middleware.clickjacking.XFrameOptionsMiddleware',
    # فقط در توسعه: صفحه‌ی ۴۰۴ سایت به‌جای صفحه‌ی زرد دیباگ جنگو.
    # آخرِ فهرست است تا پیش از بقیه پاسخ را ببیند؛ با DEBUG=False خودش
    # را کنار می‌کشد. apps/pages/middleware.py
    'apps.pages.middleware.DebugNotFoundMiddleware',
]

#  صفحه‌ی دیباگ ۴۰۴ جنگو را لازم دارید (مثلاً فهرست الگوهای نشانی)؟
#  در .env بنویسید DEBUG_ERROR_PAGES=False
DEBUG_ERROR_PAGES = config('DEBUG_ERROR_PAGES', default=True, cast=bool)


TEMPLATES = [
    {
        'BACKEND': 'django.template.backends.django.DjangoTemplates',
        'DIRS': [BASE_DIR / 'templates'],
        'APP_DIRS': True,
        'OPTIONS': {
            'context_processors': [
                'django.template.context_processors.request',
                'django.template.context_processors.static',
                'django.contrib.auth.context_processors.auth',
                'django.contrib.messages.context_processors.messages',
                'apps.pages.context_processors.site',
            ],
        },
    },
]


# ─────────────────────────────────────────────────────────────────────
#  دیتابیس
# ─────────────────────────────────────────────────────────────────────
#
#  SQLite برای توسعه. دو تنظیم مهم:
#
#  WAL          خواندن و نوشتن همزمان را ممکن می‌کند. بدون آن هر بار که
#               کسی سفارشی ثبت می‌کند، بقیه‌ی درخواست‌ها قفل می‌شوند.
#  IMMEDIATE    تراکنش از همان ابتدا قفل نوشتن می‌گیرد، نه وسط کار. جلوی
#               «database is locked» در تراکنش‌های چندمرحله‌ای را می‌گیرد.
#
#  برای تولید DATABASE_ENGINE را روی postgresql بگذارید.

if config('DATABASE_ENGINE', default='sqlite') == 'postgresql':
    DATABASES = {
        'default': {
            'ENGINE': 'django.db.backends.postgresql',
            'NAME': config('DATABASE_NAME', default='rozet'),
            'USER': config('DATABASE_USER', default='rozet'),
            'PASSWORD': config('DATABASE_PASSWORD', default=''),
            'HOST': config('DATABASE_HOST', default='127.0.0.1'),
            'PORT': config('DATABASE_PORT', default='5432'),
            'CONN_MAX_AGE': 60,
            'CONN_HEALTH_CHECKS': True,
            'OPTIONS': {'connect_timeout': 5},
        }
    }
else:
    DATABASES = {
        'default': {
            'ENGINE': 'django.db.backends.sqlite3',
            'NAME': BASE_DIR / 'db.sqlite3',
            'OPTIONS': {
                'timeout': 20,
                'transaction_mode': 'IMMEDIATE',
                'init_command': (
                    'PRAGMA journal_mode=WAL;'
                    'PRAGMA synchronous=NORMAL;'
                    'PRAGMA foreign_keys=ON;'
                    'PRAGMA busy_timeout=20000;'
                ),
            },
        }
    }


# ─────────────────────────────────────────────────────────────────────
#  کاربر و احراز هویت
# ─────────────────────────────────────────────────────────────────────
#
#  AUTH_USER_MODEL باید پیش از اولین migrate درست باشد. عوض‌کردنش بعد از
#  آن یعنی پاک‌کردن دیتابیس یا مهاجرت دستی.

AUTH_USER_MODEL = 'accounts.User'

# ─────────────────────────────────────────────────────────────────────
#  کارکنان
# ─────────────────────────────────────────────────────────────────────
#
#  خانه‌ی کارکنان پس از ورود: تابلوی سفارش‌ها (apps.staffpanel).
#  پنل جنگو (/admin/) سر جایش هست و مدیر از نوار بالای تابلو به آن می‌رود.
STAFF_HOME_URL = config('STAFF_HOME_URL', default='/staff/')

#  تابلو هر چند ثانیه یک‌بار سفارش‌های تازه را می‌پرسد. اتصال زنده
#  (WebSocket) لازم ندارد: یک کافه در روز چند ده سفارش دارد نه هزار.
STAFF_BOARD_POLL_SECONDS = config('STAFF_BOARD_POLL_SECONDS', default=20, cast=int)

#  نشست کارکنان کوتاه‌تر از مشتری است: مرورگرِ رهاشده روی پیشخان کافه
#  نباید تا دو هفته باز بماند.
STAFF_SESSION_SECONDS = config('STAFF_SESSION_SECONDS', default=60 * 60 * 12, cast=int)

LOGIN_URL = '/auth/'
LOGIN_REDIRECT_URL = '/account/'
LOGOUT_REDIRECT_URL = '/'

#  قاعده‌ی رمز — یک جا، برای همه‌ی مسیرها: ثبت‌نام، تغییر رمز در پنل
#  کاربری، ساخت کاربر در پنل مدیریت و changepassword. جاوااسکریپت و
#  متن راهنمای فرم‌ها هم همین عدد را از سرور می‌گیرند.
#
#  عمداً سبک: حداقل طول، و ردکردن رمزهای خیلی رایج («123456»،
#  «password»). دو قاعده‌ی سخت‌گیرِ جنگو برداشته شد — «فقط عدد نباشد» و
#  «شبیه شماره/نام نباشد» — چون مشتری را سر ثبت‌نام فراری می‌داد.
PASSWORD_MIN_LENGTH = config('PASSWORD_MIN_LENGTH', default=6, cast=int)

AUTH_PASSWORD_VALIDATORS = [
    {'NAME': 'django.contrib.auth.password_validation.MinimumLengthValidator',
     'OPTIONS': {'min_length': PASSWORD_MIN_LENGTH}},
    {'NAME': 'django.contrib.auth.password_validation.CommonPasswordValidator'},
]


# ─────────────────────────────────────────────────────────────────────
#  کد یک‌بارمصرف
# ─────────────────────────────────────────────────────────────────────

OTP_LENGTH = 6
OTP_TTL_SECONDS = 120            # شمارش معکوس تمپلیت
OTP_RESEND_COOLDOWN = 60
OTP_MAX_ATTEMPTS = 5
OTP_MAX_PER_HOUR = 5             # سقف ارسال به یک شماره


# ─────────────────────────────────────────────────────────────────────
#  زبان و زمان
# ─────────────────────────────────────────────────────────────────────

LANGUAGE_CODE = 'fa-ir'
TIME_ZONE = 'Asia/Tehran'
USE_I18N = True
USE_TZ = True
USE_THOUSAND_SEPARATOR = False   # جداکننده را خودمان با فیلتر فارسی می‌گذاریم

LOCALE_PATHS = [BASE_DIR / 'locale']


# ─────────────────────────────────────────────────────────────────────
#  فایل‌های ساکن و رسانه
# ─────────────────────────────────────────────────────────────────────

STATIC_URL = '/static/'
STATICFILES_DIRS = [BASE_DIR / 'static']
STATIC_ROOT = BASE_DIR / 'staticfiles'

MEDIA_URL = '/media/'
MEDIA_ROOT = BASE_DIR / 'media'

# عکس‌هایی که مشتری برای چاپ روی کیک می‌فرستد گاهی عکس خانوادگی‌اند.
# بیرون از MEDIA_ROOT ذخیره می‌شوند تا وب‌سرور مستقیم سروشان نکند؛ فقط
# یک ویوی مجوزدار می‌تواند بخواندشان.
PRIVATE_MEDIA_ROOT = BASE_DIR / 'private-media'

STORAGES = {
    'default': {
        'BACKEND': 'django.core.files.storage.FileSystemStorage',
    },
    # فایل‌های خصوصی (تصویر طرح کیک اختصاصی) بیرون از MEDIA_ROOT
    # می‌نشینند تا وب‌سرور مستقیم سروشان نکند. کلاس اختصاصی است چون
    # FileSystemStorage بدون base_url به MEDIA_URL برمی‌گردد و نشانیِ
    # نادرستِ «/media/…» می‌سازد؛ این یکی به‌جایش خطا می‌دهد.
    'private': {
        'BACKEND': 'apps.common.storage.PrivateStorage',
        'OPTIONS': {'location': PRIVATE_MEDIA_ROOT},
    },
    'staticfiles': {
        'BACKEND': (
            'django.contrib.staticfiles.storage.StaticFilesStorage' if DEBUG
            else 'django.contrib.staticfiles.storage.ManifestStaticFilesStorage'
        ),
    },
}

FILE_UPLOAD_MAX_MEMORY_SIZE = 5 * 1024 * 1024
DATA_UPLOAD_MAX_MEMORY_SIZE = 10 * 1024 * 1024
DATA_UPLOAD_MAX_NUMBER_FILES = 10         # ویزارد حداکثر ۴ تصویر می‌گیرد
DATA_UPLOAD_MAX_NUMBER_FIELDS = 500



# ─────────────────────────────────────────────────────────────────────
#  نشست، پیام و امنیت
# ─────────────────────────────────────────────────────────────────────

SESSION_ENGINE = 'django.contrib.sessions.backends.db'
SESSION_COOKIE_AGE = 60 * 60 * 24 * 14
SESSION_COOKIE_HTTPONLY = True
SESSION_COOKIE_SAMESITE = 'Lax'
CSRF_COOKIE_SAMESITE = 'Lax'
CSRF_COOKIE_HTTPONLY = False      # تمپلیت با fetch توکن را می‌خواند

SECURE_CONTENT_TYPE_NOSNIFF = True
SECURE_REFERRER_POLICY = 'strict-origin-when-cross-origin'
X_FRAME_OPTIONS = 'DENY'

if not DEBUG:
    SECURE_SSL_REDIRECT = True
    SESSION_COOKIE_SECURE = True
    CSRF_COOKIE_SECURE = True
    SECURE_HSTS_SECONDS = 60 * 60 * 24 * 365
    SECURE_HSTS_INCLUDE_SUBDOMAINS = True
    SECURE_HSTS_PRELOAD = True
    SECURE_PROXY_SSL_HEADER = ('HTTP_X_FORWARDED_PROTO', 'https')

MESSAGE_STORAGE = 'django.contrib.messages.storage.session.SessionStorage'


# ─────────────────────────────────────────────────────────────────────
#  ایمیل
# ─────────────────────────────────────────────────────────────────────

if DEBUG:
    EMAIL_BACKEND = 'django.core.mail.backends.console.EmailBackend'
else:
    EMAIL_BACKEND = 'django.core.mail.backends.smtp.EmailBackend'
    EMAIL_HOST = config('EMAIL_HOST', default='')
    EMAIL_PORT = config('EMAIL_PORT', default=587, cast=int)
    EMAIL_HOST_USER = config('EMAIL_HOST_USER', default='')
    EMAIL_HOST_PASSWORD = config('EMAIL_HOST_PASSWORD', default='')
    EMAIL_USE_TLS = True

DEFAULT_FROM_EMAIL = config('DEFAULT_FROM_EMAIL', default='ROZET <no-reply@localhost>')


# ─────────────────────────────────────────────────────────────────────
#  کش
# ─────────────────────────────────────────────────────────────────────

# کش در حافظه‌ی خود پروسه. برای یک قنادی کافی است؛ ردیس یعنی یک
# سرویس جدا که باید بالا نگه داشته و مانیتور شود، بدون آنکه در این
# اندازه چیزی اضافه کند.
CACHES = {'default': {
    'BACKEND': 'django.core.cache.backends.locmem.LocMemCache',
    'LOCATION': 'rozet',
}}


# ─────────────────────────────────────────────────────────────────────
#  قنادی
# ─────────────────────────────────────────────────────────────────────
#
#  رُزِت یک شعبه دارد و این مشخصات سالی یک‌بار هم عوض نمی‌شوند، پس
#  ثابت می‌مانند و از همین‌جا به قالب‌ها می‌روند.

CAFE = {
    'name': 'رُزِت',
    'province': 'خراسان رضوی',
    'city': 'مشهد',
    'address': 'بلوار قرنی',
    'postal_code': '',
    'landline': '',
    'latitude': None,
    'longitude': None,
    'instagram': '',
    'telegram': '',
    'whatsapp': '',
}

#  ساعت کار — یک منبع برای دو مصرف: متن فارسیِ فوتر و «درباره ما»
#  (CAFE['hours']) و ساختار ماشین‌خوانِ گوگل (openingHoursSpecification).
#  دو فهرست جدا یعنی روزی که ساعت عوض شود، گوگل ساعت قدیمی را نشان
#  می‌دهد. روزها به نام schema.org (انگلیسی) و ساعت‌ها ۲۴ساعته.
OPENING_HOURS = [
    ('شنبه تا پنجشنبه',
     ('Saturday', 'Sunday', 'Monday', 'Tuesday', 'Wednesday', 'Thursday'),
     '10:00', '21:00'),
    ('جمعه', ('Friday',), '11:00', '19:00'),
]


def _fa_hour(value):
    return str(int(value.split(':')[0])).translate(str.maketrans('0123456789', '۰۱۲۳۴۵۶۷۸۹'))


CAFE['hours'] = [(label, f'{_fa_hour(opens)} تا {_fa_hour(closes)}')
                 for label, _days, opens, closes in OPENING_HOURS]


# ─────────────────────────────────────────────────────────────────────
#  سئو
# ─────────────────────────────────────────────────────────────────────
#
#  نشانی اصلی سایت با https و بدون / پایانی، مثل  https://example.ir
#  تا وقتی خالی است، نشانی‌های مطلق (canonical، og، sitemap، JSON-LD) از
#  خودِ درخواست ساخته می‌شوند. روی سرور حتماً پر شود: بدون آن، هر
#  نام دیگری که به سرور برسد (IP، www/بی‌www) نسخه‌ی تکراری می‌سازد.
SITE_URL = config('SITE_URL', default='').rstrip('/')

#  روی سرور آزمایشی خاموش شود تا گوگل نسخه‌ی تست را ایندکس نکند.
SEO_INDEXING = config('SEO_INDEXING', default=True, cast=bool)

#  کد تأیید مالکیت در Search Console گوگل و Webmaster بینگ.
GOOGLE_SITE_VERIFICATION = config('GOOGLE_SITE_VERIFICATION', default='')
BING_SITE_VERIFICATION = config('BING_SITE_VERIFICATION', default='')

# ─────────────────────────────────────────────────────────────────────
#  درگاه پرداخت
# ─────────────────────────────────────────────────────────────────────
#
#  تا وصل‌شدن زرین‌پال، پرداخت‌ها با درگاه آزمایشی ثبت می‌شوند: بی‌درنگ
#  «موفق» می‌شوند تا چرخه‌ی خرید کامل کار کند، ولی با کانال «sandbox»
#  علامت می‌خورند و پول واقعی نیستند.
#
#  برای وصل‌کردن درگاه واقعی فقط همین یک خط عوض می‌شود:
#      PAYMENT_GATEWAY = 'apps.payments.gateway.ZarinPalGateway'
#
PAYMENT_GATEWAY = config(
    'PAYMENT_GATEWAY', default='apps.payments.gateway.SandboxGateway')

ZARINPAL_MERCHANT_ID = config('ZARINPAL_MERCHANT_ID', default='')

# نماد اعتماد — پیش‌شرط گرفتن درگاه پرداخت است.
ENAMAD_HTML = ''


# ─────────────────────────────────────────────────────────────────────
#  قواعد کسب‌وکار
# ─────────────────────────────────────────────────────────────────────
#
#  همه‌ی مبالغ به ریال‌اند. تمپلیت تومان نشان می‌دهد و درگاه ریال
#  می‌گیرد؛ تبدیل فقط در همین دو مرز انجام می‌شود.
#
#  اینجا فقط قواعد ساختاری است. نرخ‌هایی که با تورم عوض
#  می‌شوند — هزینه‌ی ارسال، بسته‌ی هدیه، بیعانه، مالیات — در
#  مدل ``common.Pricing`` هستند تا مدیر بدون دیپلوی عوضشان کند.

RIAL_PER_TOMAN = 10

CUSTOM_CAKE_MIN_DAYS = 3
CUSTOM_CAKE_CANCEL_HOURS = 18
CUSTOM_CAKE_MAX_IMAGES = 4

CHECKOUT_CALENDAR_DAYS = 7

# پله‌های باشگاه رُزِت — TIERS در account.js
LOYALTY_TIERS = [
    (0, 'تازه‌وارد', 3),
    (3, 'همیشگی', 7),
    (7, 'ویژه', 12),
    (12, 'مهمان خانه', None),
]

# ─────────────────────────────────────────────────────────────────────
#  صفحه‌ی اصلی
# ─────────────────────────────────────────────────────────────────────
#
#  کدام دسته در کدام گرید صفحه‌ی اصلی بنشیند. قرارداد بر اساس slug است
#  تا مدیر بتواند نام فارسی دسته را هر وقت خواست عوض کند بدون آنکه
#  صفحه‌ی اصلی خالی شود.
#
#  تراشه‌های فیلتر شیرینی (ماکارون، تارت، …) از زیردسته‌های «pastries»
#  ساخته می‌شوند، نه از فهرستی اینجا.

HOME_SECTIONS = {
    'cakes': 'cakes',
    'cakes_count': 6,
    'pastries': 'pastries',
    'pastries_count': 4,
}


ORDER_CODE_PREFIX = 'RZ'


# ─────────────────────────────────────────────────────────────────────
#  لاگ
# ─────────────────────────────────────────────────────────────────────

LOGGING = {
    'version': 1,
    'disable_existing_loggers': False,
    'formatters': {
        'verbose': {'format': '{asctime} {levelname} {name} {message}', 'style': '{'},
        'simple': {'format': '{levelname} {message}', 'style': '{'},
    },
    'handlers': {
        'console': {
            'class': 'logging.StreamHandler',
            'formatter': 'simple' if DEBUG else 'verbose',
        },
        'file': {
            'class': 'logging.handlers.RotatingFileHandler',
            'filename': BASE_DIR / 'logs' / 'rozet.log',
            'maxBytes': 5 * 1024 * 1024,
            'backupCount': 5,
            'encoding': 'utf-8',
            'formatter': 'verbose',
        },
    },
    'root': {'handlers': ['console', 'file'], 'level': 'INFO'},
    'loggers': {
        'django.db.backends': {'level': 'WARNING'},
        # پرداخت و ورود جداگانه لاگ می‌شوند؛ وقتی پول یا حساب کسی درگیر
        # است، «یادم نیست» جواب نیست.
        'rozet.payments': {'handlers': ['console', 'file'], 'level': 'INFO',
                           'propagate': False},
        'rozet.security': {'handlers': ['console', 'file'], 'level': 'INFO',
                           'propagate': False},
    },
}
