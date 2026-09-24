from django.urls import path

from . import views

app_name = 'pages'

urlpatterns = [
    path('about/', views.AboutView.as_view(), name='about'),

    # آخر می‌آید چون الگوی '' هر چیزی را می‌گیرد.
    path('', views.HomeView.as_view(), name='home'),
]
