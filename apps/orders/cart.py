"""
سبد خرید — روی دیتابیس، نه روی مرورگر.

تا پیش از این سبد در ``localStorage`` می‌نشست. سه اشکال داشت: با پاک‌شدن
حافظه‌ی مرورگر می‌پرید، بین گوشی و لپ‌تاپ منتقل نمی‌شد، و قیمت را خودِ
مرورگر نگه می‌داشت.

مهمان با کلید نشست سبد می‌گیرد و هنگام ورود، سبدش با حساب ادغام می‌شود.

**قیمت هیچ‌وقت از کلاینت خوانده نمی‌شود.** مرورگر فقط می‌گوید «چه
محصولی، با کدام اندازه و طعم، چندتا»؛ عدد پول را ``CartItem`` از روی
دیتابیس حساب می‌کند.
"""

import json

from django.db import transaction
from django.http import JsonResponse
from django.views import View

from apps.catalog.models import Product
from apps.common.money import rial_to_toman

from .models import Cart, CartItem

# سقف‌ها: سبد با هزار ردیف نه برای مشتری معنی دارد نه برای آشپزخانه.
MAX_ROWS = 40
MAX_QTY = 99

# کلید سبد مهمان، داخل خودِ نشست — تا از چرخش کلید هنگام ورود رد شود.
SESSION_CART_KEY = 'rozet_cart_key'


def _session_key(request):
    if not request.session.session_key:
        request.session.save()
    return request.session.session_key


def get_cart(request, create=True):
    """
    سبد این درخواست.

    کاربر واردشده سبدِ حسابش را می‌گیرد، مهمان سبدِ نشستش را.
    """
    if request.user.is_authenticated:
        if not create:
            return Cart.objects.filter(user=request.user).first()
        cart, _ = Cart.objects.get_or_create(user=request.user)
        return cart

    key = request.session.session_key
    if not key:
        if not create:
            return None
        key = _session_key(request)
    if not create:
        return Cart.objects.filter(session_key=key, user__isnull=True).first()

    cart, _ = Cart.objects.get_or_create(session_key=key, user=None)
    # کلید در خودِ نشست هم نوشته می‌شود. دلیلش ظریف است: جنگو هنگام
    # ورود اول ``cycle_key()`` می‌زند و بعد سیگنال را می‌فرستد، پس آن
    # لحظه ``session_key`` دیگر کلید مهمان نیست. ولی *داده‌ی* نشست از
    # چرخش جان سالم به در می‌برد، پس سبد از همین‌جا پیدا می‌شود.
    if request.session.get(SESSION_CART_KEY) != key:
        request.session[SESSION_CART_KEY] = key
    return cart


def merge_into_user(user, session_key):
    """
    سبد مهمان را به سبد حساب می‌ریزد — هنگام ورود یا ثبت‌نام.

    ادغام است نه جایگزینی: کسی که روی لپ‌تاپ سه کیک در سبد داشته و حالا
    از گوشی وارد می‌شود، نباید سبد قبلی‌اش را از دست بدهد.
    """
    if not session_key:
        return
    guest = Cart.objects.filter(session_key=session_key, user__isnull=True).first()
    if guest is None:
        return

    mine, _ = Cart.objects.get_or_create(user=user)
    with transaction.atomic():
        for item in guest.items.prefetch_related('addons'):
            addons = list(item.addons.all())
            twin = _find_twin(mine, item.product_id, item.size_id, item.flavor_id,
                              [a.pk for a in addons], item.message_on_cake)
            if twin:
                twin.quantity = min(MAX_QTY, twin.quantity + item.quantity)
                twin.save(update_fields=['quantity', 'updated_at'])
            else:
                item.pk = None
                item.cart = mine
                item.save()
                item.addons.set(addons)
        guest.delete()


def _find_twin(cart, product_id, size_id, flavor_id, addon_ids, message):
    """ردیفی با همان محصول و همان گزینه‌ها — برای جمع‌کردن تعداد."""
    wanted = set(addon_ids)
    for row in cart.items.filter(product_id=product_id, size_id=size_id,
                                 flavor_id=flavor_id,
                                 message_on_cake=message).prefetch_related('addons'):
        if {a.pk for a in row.addons.all()} == wanted:
            return row
    return None


def cart_payload(cart):
    """
    شکلی که ``cart.js`` می‌شناسد.

    ``meta`` همان رشته‌ی نمایشی تمپلیت است («۶ تا ۸ نفر · خامه وانیل»)
    و اینجا از روی گزینه‌های واقعی ساخته می‌شود، نه از چیزی که مرورگر
    فرستاده.
    """
    if cart is None:
        return []

    rows = (cart.items
            .select_related('product', 'size', 'flavor')
            .prefetch_related('addons', 'product__images'))

    out = []
    for row in rows:
        bits = [x for x in (row.size.label if row.size_id else '',
                            row.flavor.label if row.flavor_id else '') if x]
        bits += [addon.label for addon in row.addons.all()]
        if row.message_on_cake:
            bits.append(f'پیام: «{row.message_on_cake}»')

        cover = row.product.cover
        out.append({
            'row': row.pk,
            'id': row.product_id,
            'name': row.product.name,
            'meta': ' · '.join(bits),
            'price': rial_to_toman(row.unit_price_rial),
            'img': cover.image.url if cover else '',
            'qty': row.quantity,
            # گزینه‌ها برمی‌گردند تا اگر همین آرایه دوباره ذخیره شود،
            # ردیف هویتش را از دست ندهد.
            'size': row.size_id,
            'flavor': row.flavor_id,
            'addons': sorted(addon.pk for addon in row.addons.all()),
            'plaque': row.message_on_cake,
        })
    return out


def _clean_rows(raw):
    """
    ورودی مرورگر را به ردیف‌های قابل‌اعتماد تبدیل می‌کند.

    هر چیزی که عدد نیست دور ریخته می‌شود و قیمت اصلاً خوانده نمی‌شود.
    """
    rows = []
    for entry in raw[:MAX_ROWS]:
        if not isinstance(entry, dict):
            continue
        try:
            product_id = int(entry.get('id'))
            # «or 1» ننویس: qty صفر یعنی «این ردیف برود»، و با or به یک
            # تبدیل می‌شد — کاربر حذف می‌زد و یکی برمی‌گشت.
            raw_qty = entry.get('qty')
            quantity = 1 if raw_qty is None else int(raw_qty)
        except (TypeError, ValueError):
            continue
        if quantity < 1:
            continue

        def opt(name):
            value = entry.get(name)
            try:
                return int(value) if value not in (None, '', False) else None
            except (TypeError, ValueError):
                return None

        addons = entry.get('addons') or []
        addon_ids = []
        if isinstance(addons, list):
            for addon in addons[:10]:
                try:
                    addon_ids.append(int(addon))
                except (TypeError, ValueError):
                    pass

        rows.append({
            'product': product_id,
            'size': opt('size'),
            'flavor': opt('flavor'),
            'addons': addon_ids,
            'plaque': str(entry.get('plaque') or '')[:60],
            'qty': min(MAX_QTY, quantity),
        })
    return rows


@transaction.atomic
def replace_items(cart, raw):
    """
    سبد را با آنچه مرورگر فرستاده بازمی‌سازد.

    جایگزینی کامل است نه افزودن تکی: سه صفحه‌ی سایت هر کدام آرایه‌ی سبد
    را در حافظه نگه می‌دارند و پس از هر تغییر کلش را می‌فرستند. یک اکشن
    idempotent به‌مراتب ساده‌تر از چهار اکشنِ افزودن/کم‌کردن/حذف است و
    هیچ حالت ناهمگامی نمی‌سازد.
    """
    rows = _clean_rows(raw if isinstance(raw, list) else [])

    # فقط محصول منتشرشده و موجود. محصولی که از ویترین برداشته شده نباید
    # از راه سبدِ کهنه‌ی یک مرورگر دوباره سفارش شود.
    valid = set(Product.objects.in_stock()
                .filter(pk__in=[r['product'] for r in rows])
                .values_list('pk', flat=True))

    cart.items.all().delete()

    merged = {}
    for row in rows:
        if row['product'] not in valid:
            continue
        signature = (row['product'], row['size'], row['flavor'],
                     tuple(sorted(row['addons'])), row['plaque'])
        merged[signature] = min(MAX_QTY, merged.get(signature, 0) + row['qty'])

    for (product_id, size_id, flavor_id, addon_ids, plaque), quantity in merged.items():
        item = CartItem.objects.create(
            cart=cart, product_id=product_id,
            size_id=size_id, flavor_id=flavor_id,
            message_on_cake=plaque, quantity=quantity)
        if addon_ids:
            # فقط افزودنی‌های همین محصول؛ unit_price_rial هم دوباره
            # بررسی می‌کند، ولی ردیف بی‌ربط اصلاً نباید ذخیره شود.
            item.addons.set(item.product.addons.filter(pk__in=addon_ids))
    return cart


class CartApiView(View):
    """POST {action: 'replace', items: [...]} یا {action: 'clear'}"""

    def post(self, request):
        try:
            data = json.loads(request.body or '{}')
        except (json.JSONDecodeError, UnicodeDecodeError):
            return JsonResponse({'ok': False, 'error': 'درخواست نامعتبر است.'}, status=400)
        if not isinstance(data, dict):
            return JsonResponse({'ok': False, 'error': 'درخواست نامعتبر است.'}, status=400)

        action = data.get('action')
        if action not in {'replace', 'clear'}:
            return JsonResponse({'ok': False, 'error': 'اکشن ناشناخته.'}, status=400)

        cart = get_cart(request)
        if action == 'clear':
            cart.items.all().delete()
        else:
            replace_items(cart, data.get('items'))

        items = cart_payload(cart)
        return JsonResponse({
            'ok': True,
            'items': items,
            'count': sum(row['qty'] for row in items),
            'total': sum(row['price'] * row['qty'] for row in items),
        })
