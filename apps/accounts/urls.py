"""
آدرس‌های حساب کاربری.

پنل یک صفحه است و یک اندپوینت نوشتن. صفحه‌های ورود و ثبت‌نام بعداً
همین‌جا اضافه می‌شوند.
"""

from django.contrib.auth.views import LogoutView
from django.urls import path

from . import auth_views, staff_views, views

app_name = 'accounts'

urlpatterns = [
    # نشانی این دو باید با LOGIN_URL در settings یکی بماند.
    path('auth/', auth_views.AuthView.as_view(), name='login'),
    path('auth/api/', auth_views.AuthApiView.as_view(), name='auth_api'),

    # ورود کارکنان — جدا از ورود مشتری، با نام کاربری نه شماره.
    path('staff/login/', staff_views.StaffLoginView.as_view(), name='staff_login'),
    path('staff/login/api/', staff_views.StaffLoginApiView.as_view(),
         name='staff_login_api'),

    path('account/', views.AccountView.as_view(), name='account'),
    path('account/api/', views.AccountApiView.as_view(), name='account_api'),
    # خروج فقط با POST — لینک خروجِ GET یعنی هر تصویر یا لینکی در صفحه‌ای
    # دیگر می‌تواند کاربر را بیرون بیندازد. جنگو هم از نسخه‌ی ۵ GET را
    # نمی‌پذیرد.
    path('logout/', LogoutView.as_view(next_page='pages:home'), name='logout'),
]
