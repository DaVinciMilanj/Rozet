"""
پشتیبانی از عکس آیفون.

آیفون عکس‌ها را به‌جای JPEG با فرمت **HEIC** ذخیره می‌کند. دو مشکل
می‌سازد:

۱. Pillow بدون پکیج جانبی بازش نمی‌کند، پس جنگو آن را «تصویر نامعتبر»
   می‌شمارد و آپلود رد می‌شود.
۲. حتی اگر ذخیره شود، **هیچ مرورگری HEIC را نشان نمی‌دهد**. یعنی مشتری
   آپلود می‌کند، پیام موفقیت می‌گیرد، و آشپزخانه یک آیکن شکسته می‌بیند.

پس دو کار انجام می‌شود: باز کردن HEIC، و تبدیلش به JPEG موقع ذخیره.
بقیه‌ی فرمت‌ها دست نمی‌خورند و مثل قبل ذخیره می‌شوند.
"""

import io
import logging

from PIL import Image, ImageOps, UnidentifiedImageError

logger = logging.getLogger(__name__)

#: فرمت‌هایی که pillow-heif اضافه می‌کند — همان چیزی که دوربین آیفون
#: تولید می‌کند.
IPHONE_FORMATS = {'HEIF', 'HEIC'}

#: تنها قالب‌هایی که از مشتری پذیرفته می‌شوند → نوعی که با آن سرو
#: می‌شوند. HEIC هنگام ذخیره JPEG می‌شود (fields.ImageField)، پس نوعش
#: از همین حالا JPEG است.
UPLOAD_FORMATS = {
    'JPEG': 'image/jpeg',
    'PNG': 'image/png',
    'WEBP': 'image/webp',
    'HEIF': 'image/jpeg',
    'HEIC': 'image/jpeg',
}

_registered = False


def register_openers():
    """
    خواننده‌ی HEIC را به Pillow اضافه می‌کند.

    از ``CommonConfig.ready()`` صدا زده می‌شود تا پیش از اولین
    اعتبارسنجی فرم آماده باشد؛ وگرنه جنگو عکس آیفون را رد می‌کند.
    """
    global _registered
    if _registered:
        return
    try:
        import pillow_heif
        pillow_heif.register_heif_opener()
    except ImportError:            # pragma: no cover
        logger.warning('pillow-heif نصب نیست؛ عکس‌های HEIC آیفون باز نمی‌شوند.')
    _registered = True


def heic_to_jpeg(file):
    """
    اگر فایل HEIC بود، نسخه‌ی JPEGش را برمی‌گرداند؛ وگرنه ``None``.

    خروجی ``None`` یعنی «کاری لازم نیست» — فایل یا HEIC نیست یا اصلاً
    تصویر نیست، و در هر دو حالت دست‌نخورده به جنگو سپرده می‌شود.
    """
    register_openers()
    try:
        file.seek(0)
        image = Image.open(file)
        if image.format not in IPHONE_FORMATS:
            file.seek(0)
            return None
        image.load()
    except (UnidentifiedImageError, OSError, ValueError):
        try:
            file.seek(0)
        except (OSError, ValueError):
            pass
        return None

    with image:
        # آیفون عکس را افقی ذخیره می‌کند و زاویه‌ی درست را در EXIF
        # می‌گذارد. بدون اعمال آن، نصف عکس‌ها کج نمایش داده می‌شوند.
        image = ImageOps.exif_transpose(image)
        if image.mode != 'RGB':
            image = image.convert('RGB')
        buffer = io.BytesIO()
        image.save(buffer, format='JPEG', quality=92, optimize=True)

    file.seek(0)
    return buffer.getvalue()


def detect_upload(file):
    """
    نوع واقعی تصویرِ آپلودی، از روی **محتوا** — یا ``None``.

    پسوند و ``Content-Type`` را خودِ فرستنده تعیین می‌کند و به هیچ‌کدام
    نمی‌شود اعتماد کرد. فایلی که Pillow باز و وارسی نکند، یا قالبش در
    ``UPLOAD_FORMATS`` نباشد، تصویر حساب نمی‌شود. مهم‌ترینِ این‌ها SVG
    است: متن است، اسکریپت می‌پذیرد، و اگر برای کارمندی باز شود با نشست
    او اجرا می‌شود.
    """
    register_openers()
    try:
        file.seek(0)
        with Image.open(file) as image:
            fmt = image.format
            image.verify()
    except (UnidentifiedImageError, Image.DecompressionBombError,
            OSError, ValueError, SyntaxError):
        return None
    finally:
        try:
            file.seek(0)
        except (OSError, ValueError):
            pass
    return UPLOAD_FORMATS.get(fmt)


def downscale(file, max_dimension, quality=82):
    """
    تصویرِ بزرگ‌تر از ``max_dimension`` (ضلع بلندتر) را کوچک و WebP می‌کند؛
    وگرنه ``None``.

    عکسی که مدیر مستقیم از دوربین یا طراح آپلود می‌کند معمولاً ۲۵۰۰ پیکسل
    و نیم مگابایت است، ولی کارت محصول ۴۰۰ پیکسل نشانش می‌دهد. همان فایل
    بزرگ کُندترین جزء صفحه می‌شود — و سرعت بار شدن مستقیماً در رتبه‌ی
    گوگل (Core Web Vitals) حساب می‌شود.
    """
    try:
        file.seek(0)
        with Image.open(file) as image:
            if max(image.size) <= max_dimension:
                return None
            image = ImageOps.exif_transpose(image)
            image.thumbnail((max_dimension, max_dimension), Image.LANCZOS)
            if image.mode not in ('RGB', 'RGBA'):
                image = image.convert('RGBA' if 'A' in image.getbands() else 'RGB')
            buffer = io.BytesIO()
            image.save(buffer, format='WEBP', quality=quality, method=6)
    except (UnidentifiedImageError, OSError, ValueError):
        return None
    finally:
        try:
            file.seek(0)
        except (OSError, ValueError):
            pass
    return buffer.getvalue()
