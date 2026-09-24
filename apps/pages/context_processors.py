"""
داده‌ای که هر صفحه لازم دارد.

فوتر در همه‌ی صفحه‌ها هست و نشانی و ساعت کار می‌خواهد؛ بدون این، هر ویو
باید خودش آن‌ها را به کانتکست بدهد و اولین ویویی که یادش برود، فوتر
خالی نشان می‌دهد.
"""

from django.conf import settings

from apps.common import seo
from apps.orders.cart import cart_payload, get_cart


def site(request):
    return {
        'CAFE': settings.CAFE,
        # هدر و فوتر برای مهمان به صفحه‌ی ورود لینک می‌دهند. نشانی‌اش
        # در تمپلیت hard-code نمی‌شود تا با LOGIN_URL یکی بماند —
        # وگرنه روزی که عوض شود، login_required یک جا می‌فرستد و
        # لینک‌های صفحه جای دیگر.
        'LOGIN_URL': settings.LOGIN_URL,
        # سبد در هر صفحه‌ای لازم است: کشوی سبد در هدر مشترک است و
        # cart.js باید همگام و پیش از سه اسکریپت صفحه آن را بخواند.
        # create=False تا گشت‌زدنِ یک مهمان، الکی نشست و ردیف سبد نسازد.
        #
        # تابع است نه مقدار: جنگو callable را فقط وقتی قالب واقعاً از
        # CART_ITEMS استفاده کند صدا می‌زند. پنل مدیریت، پنل کارکنان و
        # صفحه‌های مستقل سبد ندارند و دیگر برایش کوئری نمی‌زنند.
        'CART_ITEMS': lambda: cart_payload(get_cart(request, create=False)),
        # متن راهنمای فرم‌های رمز («دست‌کم ۶ نویسه») و جاوااسکریپت
        # همین عدد را می‌خوانند، نه یک عدد جدا.
        'PASSWORD_MIN': settings.PASSWORD_MIN_LENGTH,
        # سئوی پیش‌فرض: هر صفحه‌ای که ویو خودش «seo» نساخته، دست‌کم
        # عنوان و canonical و og درست دارد. ویو با کلید هم‌نام جایگزینش
        # می‌کند (کانتکست ویو روی کانتکست processor می‌نشیند).
        'seo': seo.build(request),
        'SEO_VERIFY': {'google': settings.GOOGLE_SITE_VERIFICATION,
                       'bing': settings.BING_SITE_VERIFICATION},
    }
