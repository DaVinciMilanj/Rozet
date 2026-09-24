"""
پنل پرداخت.

همه‌چیز اینجا فقط دست مدیر است، و تراکنش موفق پس از ثبت تغییرناپذیر
می‌شود. تراکنشی که بشود ویرایشش کرد، سند نیست.
"""

from django.contrib import admin
from django.utils.html import format_html

from apps.common.admin import RoleRestrictedAdmin, TomanAdminMixin, toman_column

from .models import Gateway, Payment, PaymentState


@admin.register(Payment)
class PaymentAdmin(TomanAdminMixin, RoleRestrictedAdmin):
    list_display = ('created_at', 'order', 'gateway', 'kind', 'amount',
                    'state_badge', 'ref_id', 'recorded_by')
    list_filter = ('status', 'gateway', 'kind', 'created_at')
    search_fields = ('order__code', 'authority', 'ref_id', 'order__customer_phone')
    raw_id_fields = ('order',)
    autocomplete_fields = ('recorded_by',)
    date_hierarchy = 'created_at'
    list_select_related = ('order', 'recorded_by')

    fieldsets = (
        (None, {'fields': ('order', ('gateway', 'kind'), 'amount_rial', 'status')}),
        ('زرین‌پال', {
            'fields': (('authority', 'ref_id'), 'card_pan', 'paid_at', 'raw_response'),
            'description': 'این‌ها را خود درگاه پر می‌کند. برای دریافت حضوری خالی '
                           'می‌مانند.',
        }),
        ('ثبت دستی', {
            'fields': ('recorded_by', 'note'),
            'description': 'برای پرداخت نقدی و کارت‌خوان: چه کسی تأیید کرد که '
                           'پول دریافت شده است.',
        }),
    )

    amount = toman_column('amount_rial', 'مبلغ')

    @admin.display(description='وضعیت', ordering='status')
    def state_badge(self, obj):
        colors = {
            PaymentState.SUCCEEDED: '#3F6B57',
            PaymentState.PENDING: '#8A6115',
            PaymentState.FAILED: '#9C3B2E',
            PaymentState.CANCELED: '#9E9E9E',
        }
        return format_html('<b style="color:{}">{}</b>',
                           colors.get(obj.status, '#666'), obj.get_status_display())

    def get_readonly_fields(self, request, obj=None):
        """
        تراکنشِ ثبت‌شده قفل می‌شود.

        فقط پرداخت‌های آفلاین (نقدی، کارت‌خوان، کارت‌به‌کارت) که هنوز در
        انتظارند قابل ویرایش‌اند — چون آن‌ها را آدم ثبت می‌کند نه درگاه.
        """
        base = ('authority', 'raw_response', 'card_pan')
        if obj is None:
            return base
        if obj.status == PaymentState.SUCCEEDED or not obj.is_offline:
            return [field.name for field in self.model._meta.fields]
        return base

    def get_changeform_initial_data(self, request):
        # پرداخت آنلاین را callback زرین‌پال می‌سازد، نه آدم. رکوردی
        # که دستی اضافه می‌شود تقریباً همیشه نقدی است.
        return {'gateway': Gateway.CASH}

    def has_delete_permission(self, request, obj=None):
        return False
