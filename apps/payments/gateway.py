"""
درگاه پرداخت — با یک لایه‌ی جداکننده.

هنوز درگاهی وصل نیست، ولی جای دقیقش اینجا آماده است. بقیه‌ی پروژه
(صفحه‌ی پرداخت و ویزارد کیک اختصاصی) فقط دو تابع را صدا می‌زنند:

    start(...)    → یک ``Payment`` می‌سازد و می‌گوید کاربر کجا برود
    settle(...)   → بازگشت از درگاه را نهایی می‌کند

و هیچ‌کدام نمی‌دانند پشت این دو تابع چه خبر است. **برای وصل‌کردن
زرین‌پال فقط همین فایل عوض می‌شود** — یک کلاس تازه، و یک خط در
``settings.PAYMENT_GATEWAY``.

═══ حالت فعلی: SandboxGateway ═══
تا وصل‌شدن درگاه واقعی، پرداخت بلافاصله «موفق» ثبت می‌شود تا چرخه‌ی
خرید کامل کار کند. این ردیف‌ها **پول واقعی نیستند** و با کانال
``sandbox`` علامت خورده‌اند تا در گزارش مالی از درآمد واقعی جدا بمانند
و بعداً بشود پاکشان کرد.
"""

import logging

from django.conf import settings
from django.db import transaction
from django.utils import timezone
from django.utils.module_loading import import_string

from .models import Gateway, Payment, PaymentKind, PaymentState

logger = logging.getLogger(__name__)


class BaseGateway:
    """قراردادی که هر درگاهی باید برآورده کند."""

    #: کانالی که پرداخت‌های این درگاه با آن ثبت می‌شوند
    channel = Gateway.ZARINPAL

    def start(self, payment, request=None):
        """
        پرداخت را آغاز می‌کند.

        خروجی: نشانی‌ای که کاربر باید برود، یا ``None`` اگر لازم نیست
        جایی برود (پرداخت همان‌جا تمام شده است).
        """
        raise NotImplementedError

    def settle(self, payment, data):
        """بازگشت از درگاه را بررسی و نهایی می‌کند."""
        raise NotImplementedError


class SandboxGateway(BaseGateway):
    """
    جانشینِ درگاه، تا وقتی درگاه واقعی بیاید.

    پرداخت را بی‌درنگ موفق اعلام می‌کند. هیچ پولی جابه‌جا نمی‌شود؛
    فقط چرخه‌ی خرید قابل آزمایش و قابل نمایش می‌ماند.
    """

    channel = Gateway.SANDBOX

    def start(self, payment, request=None):
        payment.status = PaymentState.SUCCEEDED
        payment.paid_at = timezone.now()
        payment.ref_id = f'SANDBOX-{payment.pk}'
        payment.note = 'بدون درگاه واقعی ثبت شده است.'
        payment.raw_response = {'sandbox': True, 'at': payment.paid_at.isoformat()}
        payment.save(update_fields=['status', 'paid_at', 'ref_id', 'note',
                                    'raw_response', 'updated_at'])
        # جایی برای رفتن نیست؛ کاربر همان‌جا نتیجه را می‌بیند.
        return None

    def settle(self, payment, data):
        return payment.is_successful


# ═══════════════════════════════════════════════════════════════════
#  اینجا جای ZarinPalGateway است.
#
#  همین ``BaseGateway`` را پیاده کند:
#
#      class ZarinPalGateway(BaseGateway):
#          channel = Gateway.ZARINPAL
#
#          def start(self, payment, request=None):
#              # درخواست به PaymentRequest.json، گرفتن authority،
#              # ذخیره‌اش روی payment، و برگرداندن نشانی StartPay
#          def settle(self, payment, data):
#              # PaymentVerification.json و نوشتن ref_id و card_pan
#
#  و بعد در settings:  PAYMENT_GATEWAY = 'apps.payments.gateway.ZarinPalGateway'
#  هیچ جای دیگری از پروژه دست نمی‌خورد.
# ═══════════════════════════════════════════════════════════════════


def get_gateway():
    path = getattr(settings, 'PAYMENT_GATEWAY',
                   'apps.payments.gateway.SandboxGateway')
    return import_string(path)()


@transaction.atomic
def start(amount_rial, kind=PaymentKind.FULL, order=None, custom_cake=None,
          request=None):
    """
    پرداخت تازه‌ای شروع می‌کند.

    دقیقاً یکی از ``order`` یا ``custom_cake`` باید داده شود — قید
    دیتابیس هم همین را می‌گوید.

    خروجی: ``(payment, redirect_url)``؛ ``redirect_url`` وقتی ``None``
    است که کاربر لازم نیست جایی برود.
    """
    if (order is None) == (custom_cake is None):
        raise ValueError('پرداخت باید دقیقاً یک مالک داشته باشد.')
    if amount_rial <= 0:
        raise ValueError('مبلغ پرداخت باید مثبت باشد.')

    backend = get_gateway()
    payment = Payment.objects.create(
        order=order, custom_cake=custom_cake,
        gateway=backend.channel, kind=kind,
        amount_rial=amount_rial, status=PaymentState.PENDING)

    try:
        redirect = backend.start(payment, request=request)
    except Exception:                                    # noqa: BLE001
        # پرداختِ شکست‌خورده باید ردی بگذارد، نه اینکه بی‌صدا گم شود.
        logger.exception('شروع پرداخت ناموفق بود — payment=%s', payment.pk)
        payment.status = PaymentState.FAILED
        payment.save(update_fields=['status', 'updated_at'])
        raise

    payment.refresh_from_db()
    return payment, redirect
