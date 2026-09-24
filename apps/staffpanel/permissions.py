"""
دسترسی‌های پنل کارکنان — یک جدول، یک جا.

دو سطح داریم:

* **ادمین قنادی** (``kitchen``): سفارش‌ها را می‌بیند، کار را جلو می‌برد
  (شروع پخت ← آماده شد ← تحویل داده شد) و یادداشت داخلی می‌نویسد.
* **مدیر** (``manager``): همه‌ی این‌ها، به‌علاوه‌ی چیزهایی که یا پول
  جابه‌جا می‌کنند یا کار انجام‌شده را پس می‌گیرند — برگرداندن وضعیت،
  لغو سفارش، ثبت دریافت مانده، و تعیین قیمت نهایی کیک اختصاصی.

سوپریوزر همیشه مدیر است. کسی که فقط تیک ``is_staff`` دارد ولی نقشش
مشتری است، کمترین سطح را می‌گیرد: از در کارکنان رد می‌شود (همان
``can_use_staff_panel``) ولی چیزی بیش از آشپزخانه در دستش نیست.

**این جدول فقط برای نمایش نیست.** رابط کاربری از روی ``caps`` دکمه‌ها
را نشان می‌دهد یا پنهان می‌کند، ولی هر درخواست در سرور دوباره با
``can()`` سنجیده می‌شود — دکمه‌ی پنهان با DevTools برمی‌گردد.
"""

KITCHEN = 'kitchen'
MANAGER = 'manager'

# کار ← سطوحی که اجازه دارند
RULES = {
    'view':    (KITCHEN, MANAGER),   # دیدن تابلو و جزئیات
    'advance': (KITCHEN, MANAGER),   # گام بعد
    'note':    (KITCHEN, MANAGER),   # یادداشت داخلی
    'back':    (MANAGER,),           # «برگرد» — کار انجام‌شده را پس می‌گیرد
    'cancel':  (MANAGER,),           # لغو سفارش
    'settle':  (MANAGER,),           # ثبت دریافت مانده (نقدی/کارت‌خوان)
    'quote':   (MANAGER,),           # قیمت نهایی کیک اختصاصی
}

LEVEL_LABELS = {KITCHEN: 'ادمین قنادی', MANAGER: 'مدیر'}


def panel_level(user):
    """سطح کاربر در پنل، یا ``None`` اگر اصلاً راه ندارد."""
    if not (user and user.is_authenticated and user.is_active):
        return None
    if not user.can_use_staff_panel:
        return None
    if user.is_superuser or user.is_manager:
        return MANAGER
    return KITCHEN


def can(user, action):
    level = panel_level(user)
    return level is not None and level in RULES.get(action, ())


def caps(user):
    """همان جدول، برای رابط کاربری."""
    level = panel_level(user)
    return {action: level in levels for action, levels in RULES.items()}
