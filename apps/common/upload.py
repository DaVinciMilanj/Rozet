"""
مسیر ذخیره‌ی فایل‌های آپلودی.

نام اصلی فایل نگه داشته نمی‌شود. دو دلیل:

۱. نام فایل ورودی کاربر است. ``../../`` و نویسه‌های کنترلی و نام‌های
   رزروشده‌ی ویندوز (CON, PRN, NUL) همه از همین‌جا می‌آیند.
۲. نام فایلِ مشتری گاهی خودش داده‌ی شخصی است — «تولد مامان ۱۴۰۳.jpg».
"""

import functools
import uuid
from pathlib import Path

from PIL import Image
from django.utils.deconstruct import deconstructible


@functools.lru_cache(maxsize=1)
def known_extensions():
    """
    پسوندهایی که مجازند دست‌نخورده بمانند.

    فهرست دستی نوشته نمی‌شود، از خود Pillow خوانده می‌شود. دلیلش یک باگ
    واقعی است: جنگو هر تصویری را که Pillow باز کند می‌پذیرد — از جمله
    BMP و TIFF — ولی اگر پسوند در فهرست نباشد فایل با نام ``.bin``
    ذخیره می‌شود، و وب‌سرور آن را ``application/octet-stream`` سرو
    می‌کند. نتیجه: مرورگر به‌جای نمایش تصویر، دانلودش می‌کند.
    """
    Image.init()
    # SVG و PDF عمداً نیستند: هر دو می‌توانند اسکریپت داشته باشند و
    # هیچ‌کدام هم در این سایت «تصویر» نیستند.
    return set(Image.registered_extensions()) - {'.svg', '.pdf'}


@deconstructible
class UploadTo:
    """
    ``upload_to`` با نام تصادفی.

    ``deconstructible`` لازم است تا مهاجرت بتواند سریالش کند؛ بدون آن
    هر بار یک مهاجرت جدید ساخته می‌شود.
    """

    def __init__(self, folder):
        self.folder = folder.strip('/')

    def __call__(self, instance, filename):
        suffix = Path(filename).suffix.lower()
        if suffix not in known_extensions():
            suffix = '.bin'
        return f'{self.folder}/{uuid.uuid4().hex}{suffix}'

    def __eq__(self, other):
        return isinstance(other, UploadTo) and self.folder == other.folder


product_image = UploadTo('catalog/products')
category_image = UploadTo('catalog/categories')
gallery_image = UploadTo('catalog/gallery')
order_item_image = UploadTo('orders/items')

# این یکی زیر PRIVATE_MEDIA_ROOT می‌نشیند، نه MEDIA_ROOT.
custom_cake_image = UploadTo('custom-cake')
