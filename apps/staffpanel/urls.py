from django.urls import path

from . import views

app_name = 'staffpanel'

urlpatterns = [
    path('staff/', views.BoardView.as_view(), name='board'),
    path('staff/orders/<str:code>/', views.OrderDetailView.as_view(), name='order'),
    path('staff/api/', views.PanelApiView.as_view(), name='api'),
]
