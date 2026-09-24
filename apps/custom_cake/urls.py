from django.urls import path

from . import views, wizard

app_name = 'custom_cake'

urlpatterns = [
    path('custom-cake/', wizard.CustomCakeView.as_view(), name='wizard'),
    path('custom-cake/api/', wizard.CustomCakeApiView.as_view(), name='wizard_api'),

    # تصاویر خصوصی — فقط از همین مسیر و با بررسی دسترسی.
    path('private/cake-image/<int:pk>/', views.cake_image, name='image'),
]
