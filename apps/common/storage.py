"""
فضای ذخیره‌ی خصوصی.

فایل‌های این فضا بیرون از ``MEDIA_ROOT`` می‌نشینند، پس وب‌سرور مستقیم
سروشان نمی‌کند و تنها راه دیدنشان ویویی است که دسترسی را بررسی می‌کند.

چرا کلاس جدا لازم شد: ``FileSystemStorage`` وقتی ``base_url`` ندارد، به
``MEDIA_URL`` برمی‌گردد. یعنی ``image.url`` روی یک فایل خصوصی نشانی
«/media/…» می‌داد — نشانی‌ای که کار نمی‌کند ولی درست به نظر می‌رسد. هر
تمپلیتی که اشتباهاً ``.url`` صدا می‌زد، یک لینک شکسته‌ی بی‌صدا می‌ساخت.

حالا به‌جای آن استثنا می‌اندازد و می‌گوید باید از کجا بگیری.
"""

from django.core.files.storage import FileSystemStorage


class PrivateStorage(FileSystemStorage):
    def url(self, name):
        raise ValueError(
            'این فایل خصوصی است و نشانی عمومی ندارد. '
            'برای نمایشش از {% url "custom_cake:image" image.pk %} استفاده کنید.'
        )
