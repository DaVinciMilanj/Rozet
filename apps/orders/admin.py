"""
پنل سفارش‌ها.

مهم‌ترین بخش پنل، و جایی که تفاوت نقش‌ها بیشترین اثر را دارد:

* **ادمین قنادی** سفارش را می‌بیند و فقط وضعیت آماده‌سازی را جلو می‌برد.
* **مدیر** همه‌چیز، به‌علاوه‌ی برگرداندن وضعیت به عقب و ثبت پرداخت نقدی.

هر تغییر وضعیت — از هر مسیری — در ``OrderStatusHistory`` ثبت می‌شود. وقتی
سر یک سفارش اختلاف پیش بیاید، تنها چیزی که حرف می‌زند همان جدول است.
"""

from django.contrib import admin, messages
from django.db.models import F
from django.utils import timezone
from django.utils.html import format_html, format_html_join

from apps.common.admin import (ReadOnlyAdmin, RoleRestrictedAdmin,
                               TomanAdminMixin, toman_column)
from apps.common.money import format_toman
from apps.common.text import to_persian_digits

from .models import (BACKWARD_TRANSITIONS, Cart, CartItem, DeliverySlot,
                     FulfillmentStatus, Order, OrderItem, OrderItemSpec,
                     OrderStatusHistory, PaymentStatus, PromoCode)

STATUS_COLOR = {
    FulfillmentStatus.NEW: '#8A6115',
    FulfillmentStatus.BAKING: '#9C3B2E',
    FulfillmentStatus.READY: '#3F6B57',
    FulfillmentStatus.DELIVERED: '#4B5158',
    FulfillmentStatus.CANCELED: '#9E9E9E',
}


def log_status(order, field, from_value, to_value, user, reverse=False, note=''):
    """ثبت یک گذار وضعیت."""
    OrderStatusHistory.objects.create(
        order=order, field=field, from_value=from_value or '', to_value=to_value,
        changed_by=user if user and user.is_authenticated else None,
        is_reverse=reverse, note=note)


def stamp_fulfillment(order, status):
    """زمان‌های رسمی سفارش را با وضعیت هماهنگ می‌کند."""
    now = timezone.now()
    if status == FulfillmentStatus.READY:
        order.ready_at = order.ready_at or now
    elif status == FulfillmentStatus.DELIVERED:
        order.delivered_at = order.delivered_at or now
    elif status == FulfillmentStatus.CANCELED:
        order.canceled_at = now


# ═══════════════════════════════════════════════════════════════════
#  سبد خرید
# ═══════════════════════════════════════════════════════════════════

class CartItemInline(admin.TabularInline):
    model = CartItem
    extra = 0
    raw_id_fields = ('product', 'size', 'flavor')
    filter_horizontal = ('addons',)
    fields = ('product', 'size', 'flavor', 'addons', 'message_on_cake',
              'quantity', 'line_price')
    readonly_fields = ('line_price',)

    @admin.display(description='جمع ردیف')
    def line_price(self, obj):
        return f'{format_toman(obj.line_total_rial)} تومان' if obj.pk else '—'


@admin.register(Cart)
class CartAdmin(RoleRestrictedAdmin):
    """
    سبد فقط برای عیب‌یابی اینجاست.

    هیچ مبلغی در سبد ذخیره نمی‌شود؛ جمع در لحظه از روی دیتابیس ساخته
    می‌شود. برای همین ویرایش سبد از پنل هیچ اثر مالی ندارد.
    """

    list_display = ('__str__', 'user', 'item_count', 'total', 'updated_at')
    search_fields = ('user__phone', 'session_key')
    autocomplete_fields = ('user',)
    inlines = (CartItemInline,)
    date_hierarchy = 'created_at'

    def get_queryset(self, request):
        return super().get_queryset(request).select_related('user').prefetch_related(
            'items__product', 'items__size', 'items__flavor', 'items__addons')

    @admin.display(description='تعداد قلم')
    def item_count(self, obj):
        return to_persian_digits(obj.count)

    @admin.display(description='جمع')
    def total(self, obj):
        return f'{format_toman(obj.items_total_rial)} تومان'


# ═══════════════════════════════════════════════════════════════════
#  بازه‌ی تحویل
# ═══════════════════════════════════════════════════════════════════

@admin.register(DeliverySlot)
class DeliverySlotAdmin(RoleRestrictedAdmin):
    manager_only = False
    kitchen_readonly = True

    list_display = ('label', 'start_time', 'end_time', 'weekday',
                    'capacity', 'today_load', 'is_active')
    list_editable = ('capacity', 'is_active')
    list_filter = ('is_active', 'weekday')
    search_fields = ('label',)

    @admin.display(description='رزرو امروز')
    def today_load(self, obj):
        today = timezone.localdate()
        return f'{to_persian_digits(obj.booked_on(today))} از '               f'{to_persian_digits(obj.capacity)}'


# ═══════════════════════════════════════════════════════════════════
#  کد تخفیف
# ═══════════════════════════════════════════════════════════════════

@admin.register(PromoCode)
class PromoCodeAdmin(TomanAdminMixin, RoleRestrictedAdmin):
    list_display = ('code', 'kind', 'value_display', 'min_order', 'used_count',
                    'total_limit', 'is_running_now', 'is_active')
    list_filter = ('kind', 'is_active', 'first_order_only')
    search_fields = ('code', 'description')
    readonly_fields = ('used_count',)
    fieldsets = (
        (None, {'fields': ('code', 'description', ('kind', 'value'))}),
        ('شرط‌ها', {
            'fields': (('min_order_rial', 'max_discount_rial'),
                       ('starts_at', 'ends_at'),
                       ('total_limit', 'per_user_limit'),
                       'first_order_only'),
            'description': 'برای تخفیف درصدی حتماً «سقف تخفیف» را پر کنید، '
                           'وگرنه تخفیف روی سفارش بزرگ از کنترل خارج می‌شود.',
        }),
        ('وضعیت', {'fields': ('used_count', 'is_active')}),
    )

    @admin.display(description='مقدار')
    def value_display(self, obj):
        if obj.kind == 'percent':
            return f'{to_persian_digits(obj.value)}٪'
        return f'{format_toman(obj.value)} تومان'

    min_order = toman_column('min_order_rial', 'حداقل سفارش')

    @admin.display(description='فعال الان', boolean=True)
    def is_running_now(self, obj):
        return obj.is_running

# ═══════════════════════════════════════════════════════════════════
#  سفارش
# ═══════════════════════════════════════════════════════════════════

class OrderItemInline(admin.TabularInline):
    """
    اقلام سفارش.

    فقط خواندنی: قلم سفارش اسنپ‌شات است. عوض‌کردن نام یا قیمتش یعنی
    دست‌کاری سند مالی. اگر واقعاً باید تغییر کند، سفارش لغو و دوباره ثبت
    می‌شود.
    """

    model = OrderItem
    extra = 0
    can_delete = False
    fields = ('kind', 'name', 'size_label', 'flavor_label', 'message_on_cake',
              'quantity', 'unit_price', 'line_price', 'spec_summary')
    readonly_fields = fields

    def has_add_permission(self, request, obj=None):
        return False

    def get_queryset(self, request):
        return super().get_queryset(request).prefetch_related('specs')

    @admin.display(description='قیمت واحد')
    def unit_price(self, obj):
        return format_toman(obj.unit_price_rial)

    @admin.display(description='جمع')
    def line_price(self, obj):
        return format_toman(obj.line_total_rial)

    @admin.display(description='مشخصات')
    def spec_summary(self, obj):
        specs = list(obj.specs.all())
        if not specs:
            return '—'
        return format_html(
            '<ul style="margin:0;padding-inline-start:1em">{}</ul>',
            format_html_join('', '<li>{}: {}</li>',
                             ((spec.label, spec.value) for spec in specs)))


class OrderStatusHistoryInline(admin.TabularInline):
    model = OrderStatusHistory
    extra = 0
    can_delete = False
    fields = ('changed_at', 'field', 'from_value', 'to_value', 'is_reverse',
              'changed_by', 'note')
    readonly_fields = fields
    ordering = ('changed_at',)

    def has_add_permission(self, request, obj=None):
        return False


@admin.register(Order)
class OrderAdmin(TomanAdminMixin, RoleRestrictedAdmin):
    manager_only = False          # ادمین قنادی هم می‌بیند و کار می‌کند

    list_display = ('code_fa', 'customer_name', 'due_date', 'slot', 'method',
                    'status_badge', 'payment_badge', 'total', 'remaining', 'overdue')
    list_filter = ('fulfillment_status', 'payment_status', 'method', 'pay_method',
                   'due_date', 'gift_wrap')
    search_fields = ('code', 'customer_name', 'customer_phone', 'user__phone',
                     'items__name')
    date_hierarchy = 'due_date'
    ordering = ('-placed_at',)
    list_per_page = 40
    save_on_top = True
    autocomplete_fields = ('user', 'slot', 'promo', 'canceled_by')
    inlines = (OrderItemInline, OrderStatusHistoryInline)

    fieldsets = (
        ('سفارش', {'fields': ('code', ('fulfillment_status', 'payment_status'),
                              'user')}),
        ('مشتری', {'fields': (('customer_name', 'customer_phone'),
                              'allergy_note', 'customer_note')}),
        ('تحویل', {'fields': ('method', ('due_date', 'slot'), 'address_display')}),
        ('هدیه', {'classes': ('collapse',), 'fields': ('gift_wrap', 'gift_message')}),
        ('مبالغ', {
            'fields': (('items_total_rial', 'discount_rial'),
                       ('delivery_fee_rial', 'gift_wrap_rial'),
                       ('vat_percent', 'vat_rial'),
                       ('grand_total_rial', 'paid_rial'),
                       'promo', 'pay_method'),
            'description': 'مبالغ را سرور موقع ثبت سفارش حساب کرده است. '
                           'فقط «پرداخت‌شده» برای ثبت پرداخت نقدی باز است.',
        }),
        ('داخلی', {'fields': ('staff_note',)}),
        ('زمان‌ها', {'classes': ('collapse',),
                     'fields': ('placed_at', 'ready_at', 'delivered_at',
                                ('canceled_at', 'canceled_by'), 'cancel_reason',
                                'version', 'created_at', 'updated_at')}),
    )

    readonly_fields = ('code', 'address_display', 'items_total_rial', 'discount_rial',
                       'delivery_fee_rial', 'gift_wrap_rial', 'vat_rial',
                       'grand_total_rial', 'vat_percent', 'placed_at', 'ready_at',
                       'delivered_at', 'canceled_at', 'version',
                       'created_at', 'updated_at')

    def get_queryset(self, request):
        return super().get_queryset(request).select_related(
            'user', 'slot').prefetch_related('items')

    # ── ستون‌های فهرست ─────────────────────────────────────────────

    @admin.display(description='کد', ordering='code')
    def code_fa(self, obj):
        return to_persian_digits(obj.code)

    @admin.display(description='آماده‌سازی', ordering='fulfillment_status')
    def status_badge(self, obj):
        return format_html(
            '<span style="background:{};color:#fff;padding:2px 8px;'
            'border-radius:10px;font-size:11px;white-space:nowrap">{}</span>',
            STATUS_COLOR.get(obj.fulfillment_status, '#666'),
            obj.get_fulfillment_status_display())

    @admin.display(description='پرداخت', ordering='payment_status')
    def payment_badge(self, obj):
        color = '#3F6B57' if obj.payment_status == PaymentStatus.PAID else '#8A6115'
        return format_html('<span style="color:{}">{}</span>',
                           color, obj.get_payment_status_display())

    total = toman_column('grand_total_rial', 'مبلغ کل')

    @admin.display(description='مانده')
    def remaining(self, obj):
        return format_toman(obj.remaining_rial) if obj.remaining_rial else '—'

    @admin.display(description='عقب‌افتاده', boolean=True)
    def overdue(self, obj):
        return obj.is_overdue

    @admin.display(description='نشانی')
    def address_display(self, obj):
        snapshot = obj.address_snapshot or {}
        if not snapshot:
            return 'تحویل حضوری'
        parts = [snapshot.get('city'), snapshot.get('district'), snapshot.get('line')]
        line = '، '.join(part for part in parts if part)
        return format_html(
            '{}<br><small>{} — {}</small>', line,
            snapshot.get('receiver_name', ''),
            to_persian_digits(snapshot.get('receiver_phone', '')))

    # ── دسترسی ─────────────────────────────────────────────────────

    def get_readonly_fields(self, request, obj=None):
        fields = list(super().get_readonly_fields(request, obj))
        if not self._is_manager(request):
            # ادمین قنادی: فقط وضعیت آماده‌سازی و یادداشت داخلی.
            editable = {'fulfillment_status', 'staff_note'}
            fields = [field.name for field in self.model._meta.fields
                      if field.name not in editable] + ['address_display']
        if obj and obj.payment_status == PaymentStatus.REFUNDED:
            fields.append('paid_rial')
        return tuple(dict.fromkeys(fields))

    def has_delete_permission(self, request, obj=None):
        # سفارش حذف نمی‌شود؛ لغو می‌شود. حذف یعنی پاک‌کردن سند مالی.
        return False

    # ── ذخیره ──────────────────────────────────────────────────────

    def save_model(self, request, obj, form, change):
        """
        هر تغییر وضعیت را ثبت می‌کند و زمان‌های رسمی را هماهنگ می‌کند.

        گذار روبه‌عقب فقط برای مدیر مجاز است — دکمه‌ی «برگرد» تابلو هم
        همین قاعده را دارد.
        """
        if change:
            for field, log_field in (('fulfillment_status', OrderStatusHistory.Field.FULFILLMENT),
                                     ('payment_status', OrderStatusHistory.Field.PAYMENT)):
                if field not in form.changed_data:
                    continue
                old = form.initial.get(field, '')
                new = getattr(obj, field)
                reverse = (field == 'fulfillment_status'
                           and BACKWARD_TRANSITIONS.get(old) == new)
                if reverse and not self._is_manager(request):
                    setattr(obj, field, old)
                    self.message_user(
                        request, 'برگرداندن وضعیت به عقب فقط از دسترس مدیر است.',
                        level=messages.ERROR)
                    continue
                if field == 'fulfillment_status':
                    stamp_fulfillment(obj, new)
                    if new == FulfillmentStatus.CANCELED:
                        obj.canceled_by = request.user
                log_status(obj, log_field, old, new, request.user, reverse=reverse,
                           note='از پنل مدیریت')
            obj.version = F('version') + 1
        super().save_model(request, obj, form, change)
        if change:
            obj.refresh_from_db(fields=['version'])

    # ── اکشن‌ها ────────────────────────────────────────────────────

    def _advance(self, request, queryset, target):
        moved = 0
        for order in queryset:
            if not order.can_move_to(target):
                continue
            old = order.fulfillment_status
            order.fulfillment_status = target
            stamp_fulfillment(order, target)
            order.save()
            log_status(order, OrderStatusHistory.Field.FULFILLMENT, old, target,
                       request.user, note='اکشن گروهی')
            moved += 1
        skipped = queryset.count() - moved
        message = f'{moved} سفارش جابه‌جا شد.'
        if skipped:
            message += f' {skipped} سفارش در وضعیت مناسب نبود و رد شد.'
        self.message_user(request, message)

    @admin.action(description='شروع پخت')
    def action_baking(self, request, queryset):
        self._advance(request, queryset, FulfillmentStatus.BAKING)

    @admin.action(description='آماده شد')
    def action_ready(self, request, queryset):
        self._advance(request, queryset, FulfillmentStatus.READY)

    @admin.action(description='تحویل شد')
    def action_delivered(self, request, queryset):
        self._advance(request, queryset, FulfillmentStatus.DELIVERED)

    @admin.action(description='ثبت پرداخت کامل (نقدی)')
    def action_mark_paid(self, request, queryset):
        if not self._is_manager(request):
            self.message_user(request, 'فقط مدیر می‌تواند پرداخت ثبت کند.',
                              level=messages.ERROR)
            return
        count = 0
        for order in queryset.exclude(payment_status=PaymentStatus.PAID):
            old = order.payment_status
            order.paid_rial = order.grand_total_rial
            order.payment_status = PaymentStatus.PAID
            order.save(update_fields=['paid_rial', 'payment_status', 'updated_at'])
            log_status(order, OrderStatusHistory.Field.PAYMENT, old,
                       PaymentStatus.PAID, request.user, note='ثبت نقدی از پنل')
            count += 1
        self.message_user(request, f'{count} سفارش تسویه شد.')

    def get_actions(self, request):
        actions = super().get_actions(request)
        actions.pop('delete_selected', None)
        return actions

    actions = ('action_baking', 'action_ready', 'action_delivered', 'action_mark_paid')


class OrderItemSpecInline(admin.TabularInline):
    """
    مشخصات قلم — همان چیزی که سرقناد می‌خواند.

    برچسب/مقدارِ آزاد است چون تمپلیت هم روی قلم ویترینی یک نکته می‌گذارد
    و هم روی کیک اختصاصی هشت سطر مشخصات دارد.
    """

    model = OrderItemSpec
    extra = 1
    fields = ('label', 'value', 'sort_order')


@admin.register(OrderItem)
class OrderItemAdmin(RoleRestrictedAdmin):
    """
    ویرایش مشخصات یک قلم.

    اینلاین تو در تو در جنگو وجود ندارد، برای همین مشخصات از اینجا ویرایش
    می‌شوند نه از صفحه‌ی سفارش.
    """

    manager_only = False

    list_display = ('order', 'name', 'kind', 'quantity', 'message_on_cake', 'spec_count')
    list_filter = ('kind', 'order__fulfillment_status')
    search_fields = ('name', 'order__code', 'message_on_cake')
    raw_id_fields = ('order', 'product', 'custom_cake')
    inlines = (OrderItemSpecInline,)
    list_select_related = ('order',)

    readonly_fields = ('order', 'kind', 'product', 'custom_cake', 'name',
                       'size_label', 'flavor_label', 'quantity',
                       'unit_price_rial', 'line_total_rial')

    def get_queryset(self, request):
        return super().get_queryset(request).prefetch_related('specs')

    @admin.display(description='مشخصات')
    def spec_count(self, obj):
        return to_persian_digits(len(obj.specs.all()))

    def has_add_permission(self, request):
        return False


@admin.register(OrderStatusHistory)
class OrderStatusHistoryAdmin(ReadOnlyAdmin):
    manager_only = False
    list_display = ('changed_at', 'order', 'field', 'from_value', 'to_value',
                    'is_reverse', 'changed_by')
    list_filter = ('field', 'is_reverse', 'changed_at')
    search_fields = ('order__code',)
    date_hierarchy = 'changed_at'
    list_select_related = ('order', 'changed_by')
