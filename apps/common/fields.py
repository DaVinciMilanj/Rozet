"""
فیلدهای مشترک.
"""

from pathlib import Path

from django.core.files.base import ContentFile
from django.db import models

from . import images


class JSONField(models.JSONField):
    """
    JSONField که وقتی فرم مقدار خالی می‌فرستد، به default برمی‌گردد.

    مشکلی که حل می‌کند: ``models.JSONField(default=list, blank=True)`` در
    ظاهر درست است ولی نیست. پنل ادمین برای فیلد خالی صراحتاً ``None``
    می‌فرستد، و ``default`` فقط وقتی اعمال می‌شود که مقداری اصلاً ست نشده
    باشد. نتیجه:

        IntegrityError: NOT NULL constraint failed: catalog_product.flavor_notes

    و این خطا در همان اولین «افزودن محصول» در پنل درمی‌آید.

    راه‌حل بدیهی ``null=True`` است، ولی آن یعنی دو حالتِ «خالی» در
    دیتابیس — ``NULL`` و ``[]`` — که هر کوئری بعدی باید هر دو را در نظر
    بگیرد. اینجا به‌جایش قبل از ذخیره، ``None`` به default تبدیل می‌شود.
    """

    def pre_save(self, model_instance, add):
        value = super().pre_save(model_instance, add)
        if value is None and not self.null:
            value = self.get_default()
            setattr(model_instance, self.attname, value)
        return value



class ImageField(models.ImageField):
    """
    ``ImageField`` معمولی، با یک تفاوت: عکس آیفون را قبول می‌کند.

    تنها کاری که اضافه می‌کند تبدیل HEIC به JPEG پیش از ذخیره است. هیچ
    مرورگری HEIC را نشان نمی‌دهد، پس ذخیره‌ی خامش یعنی تصویر شکسته در
    پنل و در سایت.

    بقیه‌ی فرمت‌ها — JPEG، PNG، WebP، GIF و هر چیز دیگری که Pillow باز
    کند — دست‌نخورده و دقیقاً مثل ``models.ImageField`` ذخیره می‌شوند.
    """

    def __init__(self, *args, max_dimension=None, **kwargs):
        # سقف ضلع بلند برای تصویرهای عمومیِ ویترین. برای عکس چاپ روی کیک
        # نیست: آن باید با همان وضوح اصلی به چاپگر برسد.
        self.max_dimension = max_dimension
        super().__init__(*args, **kwargs)

    def deconstruct(self):
        name, path, args, kwargs = super().deconstruct()
        if self.max_dimension:
            kwargs['max_dimension'] = self.max_dimension
        return name, path, args, kwargs

    def pre_save(self, model_instance, add):
        file = getattr(model_instance, self.attname)
        # فقط فایل تازه‌آپلودشده؛ فایلی که از قبل در انبار است دوباره
        # پردازش نمی‌شود.
        if file and not file._committed:
            converted = images.heic_to_jpeg(file.file)
            if converted is not None:
                file.file = ContentFile(converted)
                file.name = f'{Path(file.name).stem or "photo"}.jpg'
            if self.max_dimension:
                smaller = images.downscale(file.file, self.max_dimension)
                if smaller is not None:
                    file.file = ContentFile(smaller)
                    file.name = f'{Path(file.name).stem or "photo"}.webp'
        return super().pre_save(model_instance, add)

    def formfield(self, **kwargs):
        field = super().formfield(**kwargs)
        # ویندوز و اندروید پسوند .heic را جزو image/* حساب نمی‌کنند و در
        # پنجره‌ی انتخاب فایل خاکستری نشانش می‌دهند. پس صریح می‌آید.
        #
        # جنگو خودش accept="image/*" را ست می‌کند، پس اینجا جایگزین
        # می‌شود — نه setdefault، که هیچ‌وقت اجرا نمی‌شد.
        if field is not None and field.widget.attrs.get('accept') in (None, 'image/*'):
            field.widget.attrs['accept'] = 'image/*,.heic,.heif'
        return field
