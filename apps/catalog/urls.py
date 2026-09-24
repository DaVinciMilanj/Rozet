from django.urls import path

from . import favorites, reviews, views

app_name = 'catalog'

urlpatterns = [
    path('products/', views.ProductListView.as_view(), name='product_list'),
    path('product/<slug:slug>/', views.ProductDetailView.as_view(),
         name='product_detail'),
    path('favorite/', favorites.FavoriteToggleView.as_view(), name='favorite_toggle'),
    path('review/', reviews.ReviewSubmitView.as_view(), name='review_submit'),
]
