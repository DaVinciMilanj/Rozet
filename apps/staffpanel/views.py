"""
پنل کارکنان — تابلوی سفارش‌ها و برگه‌ی هر سفارش.

دو صفحه و یک اندپوینت:

    /staff/                  تابلو (admin/orders در تمپلیت)
    /staff/orders/<code>/    جزئیات (admin/order-details)
    /staff/api/              GET: تازه‌کردن · POST: کار روی سفارش

هر دو صفحه داده‌ی اولیه را در ``json_script`` می‌گیرند تا بدون یک رفت‌وبرگشت
اضافه رسم شوند؛ بعد تابلو هر چند ثانیه یک‌بار از اندپوینت می‌پرسد چه
عوض شده — سفارش تازه، یا کاری که همکار دیگری از گوشی خودش کرده.

دسترسی دو لایه است و هر دو در ``permissions.py``:
    ورود به پنل   ← ``panel_level`` (کارمند، مدیر، سوپریوزر)
    هر کار        ← ``can(user, action)`` — دوباره در سرور، نه فقط در دکمه
"""

import json

from django.conf import settings
from django.http import Http404, JsonResponse
from django.shortcuts import redirect
from django.urls import reverse
from django.utils import timezone
from django.utils.http import urlencode
from django.views import View
from django.views.generic import TemplateView

from apps.common.text import parse_int

from . import services
from .payload import (board_orders, find_order, order_payload, unseen_codes,
                      unseen_notifications)
from .permissions import LEVEL_LABELS, can, caps, panel_level

# نام هر کار همان نام دسترسی‌اش در ``permissions.RULES`` است.
ACTIONS = ('advance', 'back', 'cancel', 'settle', 'quote', 'note')


def _staff_login_redirect(request):
    url = reverse('accounts:staff_login')
    return redirect(f'{url}?{urlencode({"next": request.get_full_path()})}')


def _me(user):
    level = panel_level(user)
    return {
        'name': user.get_short_name(),
        'level': level,
        'levelLabel': LEVEL_LABELS.get(level, ''),
    }


def _urls(user):
    return {
        'api': reverse('staffpanel:api'),
        'board': reverse('staffpanel:board'),
        # الگو؛ کد سفارش جای «CODE» می‌نشیند.
        'detail': reverse('staffpanel:order', args=['CODE']),
        'logout': reverse('accounts:logout'),
        'login': reverse('accounts:staff_login'),
        # پنل جنگو فقط برای کسی که واقعاً به آن راه دارد.
        'admin': reverse('admin:index') if user.is_staff else '',
    }


class StaffPageMixin:
    """
    صفحه‌های پنل: بیرونی‌ها به صفحه‌ی ورود کارکنان می‌روند.

    مشتریِ واردشده هم همان‌جا می‌رود، نه به ۴۰۳: شاید همان کسی است که
    با حساب شخصی‌اش وارد مانده و حالا می‌خواهد با حساب کاری وارد شود.
    """

    def dispatch(self, request, *args, **kwargs):
        if panel_level(request.user) is None:
            return _staff_login_redirect(request)
        return super().dispatch(request, *args, **kwargs)

    def seed(self, **extra):
        user = self.request.user
        return {
            'me': _me(user),
            'caps': caps(user),
            'urls': _urls(user),
            'poll': settings.STAFF_BOARD_POLL_SECONDS,
            'today': timezone.localdate().isoformat(),
            **extra,
        }


class BoardView(StaffPageMixin, TemplateView):
    template_name = 'staffpanel/board.html'

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        user = self.request.user
        context['seed'] = self.seed(
            orders=[order_payload(order) for order in board_orders()],
            unseen=unseen_codes(user, panel_level(user)),
        )
        return context


class OrderDetailView(StaffPageMixin, TemplateView):
    template_name = 'staffpanel/order.html'

    def get(self, request, *args, **kwargs):
        order = find_order(kwargs['code'])
        context = self.get_context_data(**kwargs)
        context['seed'] = self.seed(
            code=kwargs['code'],
            order=order_payload(order, history=True) if order else None,
        )
        # صفحه‌ی «پیدا نشد» را خودِ تمپلیت رسم می‌کند؛ فقط کد وضعیت
        # باید راست بگوید.
        return self.render_to_response(context, status=200 if order else 404)


class PanelApiView(View):
    """
    GET  /staff/api/            → {orders, unseen}            تازه‌کردن تابلو
    GET  /staff/api/?code=…     → {order}                     تازه‌کردن برگه
    POST {action, code, version, …} → {ok, order}              کار روی سفارش
    POST {action: 'seen'}       → {ok}                         زنگ باز شد

    برای بیرونی ۴۰۱ و برای بی‌دسترسی ۴۰۳ — JSON، نه ریدایرکت؛ fetch
    ریدایرکت را بی‌صدا دنبال می‌کند و HTML صفحه‌ی ورود را جای JSON
    تحویل می‌دهد.
    """

    def dispatch(self, request, *args, **kwargs):
        if not request.user.is_authenticated:
            return self.fail('نشست شما تمام شده؛ دوباره وارد شوید.', status=401)
        if panel_level(request.user) is None:
            return self.fail('به پنل کارکنان دسترسی ندارید.', status=403)
        return super().dispatch(request, *args, **kwargs)

    @staticmethod
    def fail(message, status=400, **extra):
        return JsonResponse({'ok': False, 'error': message, **extra}, status=status)

    def get(self, request):
        user = request.user
        code = request.GET.get('code')
        if code:
            order = find_order(code)
            if order is None:
                return self.fail('سفارش پیدا نشد.', status=404)
            return JsonResponse({'ok': True, 'order': order_payload(order, history=True)})
        return JsonResponse({
            'ok': True,
            'orders': [order_payload(order) for order in board_orders()],
            'unseen': unseen_codes(user, panel_level(user)),
        })

    def post(self, request):
        try:
            data = json.loads(request.body or '{}')
        except (json.JSONDecodeError, UnicodeDecodeError):
            return self.fail('درخواست نامعتبر است.')
        if not isinstance(data, dict):
            return self.fail('درخواست نامعتبر است.')

        action = data.get('action')
        user = request.user

        if action == 'seen':
            level = panel_level(user)
            user.seen_notifications.add(*unseen_notifications(user, level))
            return JsonResponse({'ok': True, 'unseen': []})

        if action not in ACTIONS:
            return self.fail('کار نامعتبر است.')
        if not can(user, action):
            return self.fail('این کار از دسترس شما بیرون است.', status=403)

        code = str(data.get('code') or '')
        version = parse_int(data.get('version'))
        try:
            if action == 'advance':
                services.advance(code, version, data.get('to'), user)
            elif action == 'back':
                services.step_back(code, version, user)
            elif action == 'cancel':
                services.cancel(code, version, data.get('reason'), user)
            elif action == 'settle':
                services.settle(code, version, data.get('channel'), user)
            elif action == 'quote':
                services.quote(code, version, data.get('price'), user)
            elif action == 'note':
                services.save_note(code, data.get('text'))
        except services.ActionError as error:
            order = find_order(code)
            return self.fail(str(error), status=error.status,
                             order=order_payload(order, history=True) if order else None)

        order = find_order(code)
        if order is None:
            raise Http404
        return JsonResponse({'ok': True, 'order': order_payload(order, history=True)})
