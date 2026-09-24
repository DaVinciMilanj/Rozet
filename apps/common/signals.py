"""
پاک‌سازی فایل‌های یتیم.

جنگو فایل را روی دیسک نگه می‌دارد حتی وقتی رکوردش رفته است. دو نشتی
می‌سازد:

۱. **جایگزینی** — مدیر تصویر محصول را عوض می‌کند؛ فایل قبلی سر جایش
   می‌ماند و هیچ‌کس دیگر نمی‌داند مال چه بوده.
۲. **حذف** — رکورد پاک می‌شود، فایل نه. با حذف آبشاری (مثلاً پاک‌کردن
   یک درخواست کیک با چهار تصویرش) چند فایل یک‌جا یتیم می‌شوند.

چرا سیگنال و نه ``Model.delete()``: حذف از چند مسیر اتفاق می‌افتد که
هیچ‌کدام ``delete()`` نمونه را صدا نمی‌زنند — حذف آبشاری، حذف گروهی
``queryset.delete()``، و اکشن گروهی پنل. هر سه‌ی این‌ها ``post_delete``
را **می‌فرستند**. این دقیقاً همان جایی است که سیگنال ابزار درست است.

(دقت: ``queryset.update()`` هیچ سیگنالی نمی‌فرستد. برای همین
جایگزینی با ``pre_save`` گرفته می‌شود، نه با آپدیت گروهی.)
"""

import logging

from django.db import models
from django.db.models.signals import post_delete, pre_save

logger = logging.getLogger(__name__)

# هر جفت (مدل، نام فیلد) که فایل نگه می‌دارد. connect() پرش می‌کند و
# _is_shared برای پیداکردن ارجاع‌های دیگر به یک مسیر از آن می‌خواند.
FILE_FIELDS = []


def _file_fields(model):
    return [f for f in model._meta.fields if isinstance(f, models.FileField)]


def _is_shared(field_file, owner):
    """
    آیا رکورد دیگری هنوز به همین مسیر اشاره می‌کند؟

    در حالت عادی هر رکورد فایل خودش را دارد. ولی اگر کدی به‌جای کپی‌کردن
    فایل، همان مسیر را در رکورد دوم بنشاند، حذف رکورد دوم فایل رکورد اول
    را هم می‌بَرد — و رکورد اول با تصویری که دیگر نیست باقی می‌ماند.

    این دقیقاً یک بار اتفاق افتاد و دو تصویر محصول را از بین برد. چند
    کوئری در لحظه‌ی حذف، بهای ارزانی برای از دست نرفتن فایل است.
    """
    name = field_file.name
    for model, field_name in FILE_FIELDS:
        rows = model._base_manager.filter(**{field_name: name})
        if model is type(owner) and owner.pk is not None:
            rows = rows.exclude(pk=owner.pk)
        if rows.exists():
            return True
    return False


def _discard(field_file, owner=None):
    """
    فایل را از انبار پاک می‌کند و هر خطایی را می‌بلعد.

    نبودِ فایل یا خطای دسترسی نباید تراکنشی را که همین الان موفق شده،
    بشکند. فایل یتیم یک ناراحتی است؛ خطا در حذف سفارش یک فاجعه.
    """
    if not field_file or not field_file.name:
        return
    try:
        if owner is not None and _is_shared(field_file, owner):
            logger.info('فایل مشترک است و نگه داشته شد: %s', field_file.name)
            return
        field_file.storage.delete(field_file.name)
    except Exception:                                    # noqa: BLE001
        logger.warning('حذف فایل ناموفق بود: %s', field_file.name, exc_info=True)


def delete_files_on_delete(sender, instance, **kwargs):
    for field in _file_fields(sender):
        _discard(getattr(instance, field.name, None), owner=instance)


def delete_files_on_replace(sender, instance, **kwargs):
    if not instance.pk:
        return
    try:
        previous = sender._default_manager.get(pk=instance.pk)
    except sender.DoesNotExist:
        return
    for field in _file_fields(sender):
        old = getattr(previous, field.name, None)
        new = getattr(instance, field.name, None)
        if old and old.name != getattr(new, 'name', None):
            _discard(old, owner=instance)


def connect():
    """
    به هر مدلی که فیلد فایل دارد وصل می‌شود.

    خودکار است تا مدل تازه‌ای که فردا اضافه شود، جا نیفتد. ``dispatch_uid``
    جلوی وصل‌شدن دوباره را می‌گیرد — ``ready()`` در بعضی حالت‌ها دو بار
    صدا زده می‌شود.
    """
    from django.apps import apps

    FILE_FIELDS.clear()
    for model in apps.get_models():
        fields = _file_fields(model)
        if not fields:
            continue
        FILE_FIELDS.extend((model, f.name) for f in fields)
        label = model._meta.label_lower
        post_delete.connect(delete_files_on_delete, sender=model,
                            dispatch_uid=f'rozet_files_delete_{label}')
        pre_save.connect(delete_files_on_replace, sender=model,
                         dispatch_uid=f'rozet_files_replace_{label}')
