"""
ورود کارکنان.

از ورود مشتری جداست و باید جدا بماند:

* مشتری با **شماره‌ی موبایل** وارد می‌شود، کارمند با **نام کاربری**.
* مشتری بعد از ورود به پنل حسابش می‌رود، کارمند به تابلوی آشپزخانه.
* حسابِ مشتری اینجا پذیرفته نمی‌شود، حتی با رمز درست.

**تأیید دومرحله‌ای فعلاً نیست.** تمپلیت پنل شش‌خانه‌ای داشت و مدل هم
``totp_secret`` و ``totp_enabled`` دارد، ولی نه کتابخانه‌ی TOTP نصب است
و نه مسیر ثبت‌نامِ اپ احراز هویت. مرحله‌ای که کار نکند بدتر از نبودنش
است، پس برداشته شد — درزش در ``_two_factor_required`` علامت خورده و
قرارداد سمت کلاینت (``twoFactor`` در پاسخ) دست‌نخورده مانده.
"""

import json

from django.conf import settings
from django.contrib.auth import login
from django.contrib.auth.hashers import check_password
from django.http import JsonResponse
from django.shortcuts import redirect
from django.utils.http import url_has_allowed_host_and_scheme
from django.views import View
from django.views.generic import TemplateView

from apps.common.text import normalize_phone

from .auth_views import _log
from .models import User

# هشِ بی‌مصرف، فقط برای برابرکردن زمانِ پاسخ وقتی نام کاربری وجود ندارد.
# بدون آن، «کاربر نیست» محسوس‌تر از «رمز غلط» جواب می‌دهد و می‌شود با
# اندازه‌گیری زمان فهمید کدام نام کاربری واقعی است.
DUMMY_HASH = ('pbkdf2_sha256$1000000$rozetdummysalt$'
              'LqCPEfSVEmdRDTDMoOxLZv8eBAmYJvtnTMM1bDGsRpU=')


def staff_home():
    """
    خانه‌ی کارکنان پس از ورود — تابلوی سفارش‌ها (``staffpanel:board``).

    از تنظیمات خوانده می‌شود تا اگر روزی خانه‌ی دیگری لازم شد، کد دست
    نخورد.
    """
    return getattr(settings, 'STAFF_HOME_URL', '/staff/')


def _safe_next(request, raw):
    if raw and url_has_allowed_host_and_scheme(
            raw, allowed_hosts={request.get_host()}, require_https=request.is_secure()):
        return raw
    return staff_home()


class StaffLoginView(TemplateView):
    """صفحه‌ی ورود کارکنان — /staff/login/"""

    template_name = 'accounts/staff_login.html'

    def dispatch(self, request, *args, **kwargs):
        user = request.user
        # کارمندی که وارد است، خودکار به پنل می‌رود؛ فرم خالیِ ورود
        # برایش فقط یک قدم اضافه است.
        if user.is_authenticated and user.can_use_staff_panel:
            return redirect(_safe_next(request, request.GET.get('next')))
        return super().dispatch(request, *args, **kwargs)

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['next'] = _safe_next(self.request, self.request.GET.get('next'))
        return context


class StaffLoginApiView(View):
    """POST {action: 'signin', username, password} → {ok, redirect}"""

    def post(self, request):
        try:
            data = json.loads(request.body or '{}')
        except (json.JSONDecodeError, UnicodeDecodeError):
            return self.fail('username', 'درخواست نامعتبر است.')
        if not isinstance(data, dict) or data.get('action') != 'signin':
            return self.fail('username', 'درخواست نامعتبر است.')

        return self._signin(request, data)

    @staticmethod
    def fail(field, message, status=400, **extra):
        return JsonResponse({'ok': False, 'field': field, 'error': message, **extra},
                            status=status)

    def _find(self, raw):
        """
        کارمند را با نام کاربری پیدا می‌کند — یا با شماره، اگر کسی
        عادت داشته باشد شماره‌اش را بزند.
        """
        value = str(raw or '').strip()
        if not value:
            return None
        user = User.objects.filter(username__iexact=value).first()
        if user is None:
            phone = normalize_phone(value)
            if phone:
                user = User.objects.filter(phone=phone).first()
        return user

    def _signin(self, request, data):
        username = str(data.get('username', '')).strip()
        password = data.get('password') or ''
        user = self._find(username)

        # یک پیام برای هر سه حالتِ «کاربر نیست»، «رمز غلط» و «کارمند
        # نیست». تفکیکشان به کسی که در می‌زند می‌گوید کدام نام کاربری
        # واقعی است.
        if user is None:
            check_password(password, DUMMY_HASH)       # زمان را برابر نگه می‌دارد
            _log(request, username, ok=False, reason='staff-no-user', is_staff_panel=True)
            return self.fail('password', 'نام کاربری یا رمز عبور درست نیست.')

        if not user.check_password(password) or not user.is_active:
            _log(request, username, user=user, ok=False,
                 reason='staff-bad-password', is_staff_panel=True)
            return self.fail('password', 'نام کاربری یا رمز عبور درست نیست.')

        if not user.can_use_staff_panel:
            # حساب مشتری اینجا کاری ندارد، حتی با رمز درست.
            _log(request, username, user=user, ok=False,
                 reason='staff-not-staff', is_staff_panel=True)
            return self.fail('password', 'نام کاربری یا رمز عبور درست نیست.')

        if self._two_factor_required(user):
            return JsonResponse({'ok': True, 'twoFactor': True})

        user.backend = 'django.contrib.auth.backends.ModelBackend'
        login(request, user)
        # ورود کارکنان کوتاه‌تر از مشتری است: یک مرورگرِ رهاشده روی
        # پیشخان کافه نباید تا دو هفته باز بماند.
        request.session.set_expiry(getattr(settings, 'STAFF_SESSION_SECONDS', 60 * 60 * 12))
        _log(request, username, user=user, ok=True, is_staff_panel=True)

        return JsonResponse({
            'ok': True,
            'name': user.get_short_name(),
            'redirect': _safe_next(request, data.get('next')),
        })

    def _two_factor_required(self, user):
        """
        ══════════ جای اتصال تأیید دومرحله‌ای ══════════

        امروز همیشه ``False`` است. وقتی TOTP وصل شود، اینجا
        ``user.totp_enabled`` بررسی می‌شود و پاسخ ``twoFactor: True``
        می‌گیرد؛ جاوااسکریپت صفحه از قبل می‌داند با آن چه کند (پنل کد
        را باز می‌کند) و فقط مارکاپ آن پنل باید برگردد.
        """
        return False
