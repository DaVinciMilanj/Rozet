"""
ورود و ثبت‌نام.

یک صفحه با دو فرم (ورود / ثبت‌نام) که هر دو به یک اندپوینت می‌زنند —
همان الگوی پنل کاربری.

**کد پیامکی و بازیابی رمز اینجا نیستند.** تمپلیت برایشان جا داشت (پنل
شش‌خانه‌ای، دکمه‌ی «رمزم را فراموش کرده‌ام»، «ورود با کد پیامکی») ولی
هنوز سامانه‌ی پیامکی وصل نیست. دکمه‌ای که کار نکند بدتر از نبودنش است،
پس برداشته شده‌اند. مدل ``OTPCode`` سر جایش می‌ماند تا روزی که پنل
پیامکی بیاید، فقط همین فایل و تمپلیت عوض شوند.
"""

import json

from django.contrib.auth import authenticate, login
from django.contrib.auth.password_validation import validate_password
from django.core.exceptions import ValidationError
from django.http import JsonResponse
from django.shortcuts import redirect
from django.urls import reverse
from django.utils.http import url_has_allowed_host_and_scheme
from django.views import View
from django.views.generic import TemplateView

from apps.common.text import fix_letters, normalize_phone

from .models import LoginAttempt, Role, User

# «مرا به خاطر بسپار» خاموش یعنی نشست با بستن مرورگر تمام شود.
REMEMBER_SECONDS = 60 * 60 * 24 * 14


def _safe_next(request, raw):
    """
    مقصد بعد از ورود.

    بدون این بررسی، ``?next=https://elsewhere/`` یک ریدایرکت باز است:
    لینکی که آدرسش به رُزِت ختم می‌شود ولی کاربر را — تازه پس از ورود
    موفق — به سایت دیگری می‌برد.
    """
    if raw and url_has_allowed_host_and_scheme(
            raw, allowed_hosts={request.get_host()}, require_https=request.is_secure()):
        return raw
    return reverse('accounts:account')


def _log(request, phone, user=None, ok=False, reason='', is_staff_panel=False):
    """
    ثبت تلاش ورود.

    فقط لاگ است و هیچ قفلی اعمال نمی‌کند — تصمیم خودِ پروژه. اگر روزی
    کسی شروع به حدس‌زدن رمز کرد، همین جدول می‌گوید از کدام IP و چند بار.
    """
    forwarded = request.META.get('HTTP_X_FORWARDED_FOR', '')
    LoginAttempt.objects.create(
        phone=phone[:40],
        user=user,
        ip=(forwarded.split(',')[0].strip() or request.META.get('REMOTE_ADDR')) or None,
        user_agent=request.META.get('HTTP_USER_AGENT', '')[:300],
        succeeded=ok,
        failure_reason=reason[:40],
        # ورود کارکنان و مشتری در یک جدول می‌نشینند ولی باید قابل
        # تفکیک باشند: تلاش ناموفق روی پنل کارکنان معنای دیگری دارد.
        is_staff_panel=is_staff_panel,
    )


class AuthView(TemplateView):
    """صفحه‌ی ورود/ثبت‌نام — /auth/"""

    template_name = 'accounts/auth.html'

    def dispatch(self, request, *args, **kwargs):
        # کاربر واردشده اینجا کاری ندارد؛ فرم خالیِ ورود برایش گیج‌کننده
        # است و دکمه‌اش هم او را به همان‌جایی می‌برد که می‌توانست مستقیم
        # برود.
        if request.user.is_authenticated:
            return redirect(_safe_next(request, request.GET.get('next')))
        return super().dispatch(request, *args, **kwargs)

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['next'] = _safe_next(self.request, self.request.GET.get('next'))
        return context


class AuthApiView(View):
    """POST {action: signin|signup, ...} → {ok, redirect} یا {ok: false, field, error}"""

    ACTIONS = {'signin', 'signup'}

    def post(self, request):
        if request.user.is_authenticated:
            return JsonResponse({'ok': True, 'redirect': reverse('accounts:account')})

        try:
            data = json.loads(request.body or '{}')
        except (json.JSONDecodeError, UnicodeDecodeError):
            return self.fail('phone', 'درخواست نامعتبر است.')
        if not isinstance(data, dict) or data.get('action') not in self.ACTIONS:
            return self.fail('phone', 'درخواست نامعتبر است.')

        return getattr(self, '_' + data['action'])(request, data)

    @staticmethod
    def fail(field, message, status=400):
        """``field`` می‌گوید پیام زیر کدام ورودی بنشیند."""
        return JsonResponse({'ok': False, 'field': field, 'error': message}, status=status)

    def _remember(self, request, data):
        if not data.get('remember'):
            request.session.set_expiry(0)
        else:
            request.session.set_expiry(REMEMBER_SECONDS)

    # ── ورود ───────────────────────────────────────────────────────

    def _signin(self, request, data):
        phone = normalize_phone(data.get('phone', ''))
        password = data.get('password') or ''

        user = authenticate(request, username=phone, password=password)
        if user is None:
            # یک پیام برای هر دو حالتِ «شماره نیست» و «رمز غلط». تفکیکشان
            # به مهاجم می‌گوید کدام شماره در سایت حساب دارد.
            _log(request, phone, reason='bad-credentials')
            return self.fail('password', 'شماره یا رمز عبور درست نیست.')

        login(request, user)
        self._remember(request, data)
        _log(request, phone, user=user, ok=True)
        return JsonResponse({
            'ok': True,
            'name': user.get_short_name(),
            'redirect': _safe_next(request, data.get('next')),
        })

    # ── ثبت‌نام ────────────────────────────────────────────────────

    def _signup(self, request, data):
        phone = normalize_phone(data.get('phone', ''))
        password = data.get('password') or ''
        full_name = fix_letters(str(data.get('name', ''))).strip()

        if len(full_name) < 3:
            return self.fail('name', 'نام و نام خانوادگی را کامل بنویسید.')
        # همان قاعده‌ی تغییر رمز و پنل مدیریت (AUTH_PASSWORD_VALIDATORS)؛
        # پیش‌تر اینجا فقط طول سنجیده می‌شد و دو مسیر دو قاعده داشتند.
        try:
            validate_password(password)
        except ValidationError as error:
            return self.fail('password', ' '.join(error.messages))

        # شماره شناسه‌ی ورود است، پس تکراری بودنش را پیش از ساخت
        # می‌گوییم — نه با IntegrityError.
        if User.objects.filter(phone=phone).exists():
            return self.fail('phone', 'این شماره قبلاً ثبت شده است؛ وارد شوید.')

        first, _, last = full_name.partition(' ')
        try:
            user = User.objects.create_user(
                phone=phone, password=password,
                first_name=first[:60], last_name=last.strip()[:60],
                role=Role.CUSTOMER)
        except ValidationError as error:
            # create_user خودش full_clean می‌زند؛ تنها خطای محتمل، شماره‌ی
            # بدشکل است.
            messages = sum(error.message_dict.values(), [])
            return self.fail('phone', ' '.join(messages) or 'شماره موبایل درست نیست.')

        # بدون پنل پیامکی راهی برای تأیید شماره نداریم، پس حساب
        # تأییدنشده می‌ماند و همین‌طور هم باید بماند: هر روز که
        # is_phone_verified را الکی True کنیم، روزی که پیامک وصل شود
        # نمی‌دانیم کدام شماره واقعاً تأیید شده است.
        user.backend = 'django.contrib.auth.backends.ModelBackend'
        login(request, user)
        self._remember(request, data)
        _log(request, phone, user=user, ok=True, reason='signup')
        return JsonResponse({
            'ok': True,
            'name': user.get_short_name(),
            'redirect': _safe_next(request, data.get('next')),
        })
