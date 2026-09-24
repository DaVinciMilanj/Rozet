"""
ادغام سبد مهمان با حساب، هنگام ورود.

کاربر کیک را در سبد می‌گذارد، بعد وارد می‌شود تا سفارش ثبت کند. اگر
ورود سبد را دور بیندازد، دقیقاً در حساس‌ترین لحظه خریدش را از دست داده
است.

چرا سیگنال: ``login()`` هم از صفحه‌ی ورود صدا زده می‌شود، هم از
ثبت‌نام، و فردا شاید از جای دیگر. ``user_logged_in`` تنها نقطه‌ای است
که هر سه از آن رد می‌شوند.

نکته‌ی ترتیب — و تنها جای ظریف این فایل: جنگو هنگام ورود **اول**
``cycle_key()`` می‌زند (برای جلوگیری از session fixation) و **بعد**
این سیگنال را می‌فرستد. پس ``request.session.session_key`` دیگر کلید
مهمان نیست و جست‌وجو با آن هیچ سبدی پیدا نمی‌کند.

ولی *داده‌ی* نشست از چرخش رد می‌شود. برای همین ``get_cart`` کلید را
در خودِ نشست هم می‌نویسد و اینجا از همان‌جا خوانده می‌شود.
"""

import logging

from django.contrib.auth.signals import user_logged_in
from django.dispatch import receiver

from .cart import SESSION_CART_KEY, merge_into_user

logger = logging.getLogger(__name__)


@receiver(user_logged_in, dispatch_uid='rozet_merge_cart_on_login')
def merge_cart_on_login(sender, request, user, **kwargs):
    if request is None:
        return
    key = request.session.pop(SESSION_CART_KEY, None)
    if not key:
        return
    try:
        merge_into_user(user, key)
    except Exception:                                    # noqa: BLE001
        # سبد ادغام‌نشده ناراحت‌کننده است؛ ورودِ شکست‌خورده فاجعه.
        logger.warning('ادغام سبد هنگام ورود ناموفق بود.', exc_info=True)
