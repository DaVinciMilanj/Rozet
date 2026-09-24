"""
پنل اعلان‌ها.
"""

from django.contrib import admin

from apps.common.admin import RoleRestrictedAdmin
from apps.common.text import to_persian_digits

from .models import StaffNotification


@admin.register(StaffNotification)
class StaffNotificationAdmin(RoleRestrictedAdmin):
    manager_only = False
    kitchen_readonly = True

    list_display = ('created_at', 'kind', 'title', 'target_roles',
                    'is_urgent', 'seen_count')
    list_filter = ('kind', 'is_urgent', 'created_at')
    search_fields = ('title', 'body', 'order__code')
    raw_id_fields = ('order', 'cake_request')
    filter_horizontal = ('seen_by',)
    date_hierarchy = 'created_at'

    fields = ('kind', 'title', 'body', ('order', 'cake_request'),
              'target_roles', 'is_urgent', 'seen_by')

    def get_queryset(self, request):
        return super().get_queryset(request).prefetch_related('seen_by')

    @admin.display(description='دیده شده')
    def seen_count(self, obj):
        return to_persian_digits(len(obj.seen_by.all()))
