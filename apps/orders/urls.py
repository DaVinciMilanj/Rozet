"""
نشانی‌های سبد و پرداخت.
"""

from django.urls import path

from . import cart, checkout

app_name = 'orders'

urlpatterns = [
    path('cart/api/', cart.CartApiView.as_view(), name='cart_api'),

    path('checkout/', checkout.CheckoutView.as_view(), name='checkout'),
    path('checkout/api/', checkout.CheckoutApiView.as_view(), name='checkout_api'),
]
