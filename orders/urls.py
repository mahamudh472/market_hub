from django.urls import path
from . import views

urlpatterns = [
    path('', views.OrderListView.as_view(), name='order-list'),
    path('<uuid:pk>/', views.OrderDetailView.as_view(), name='order-detail'),
    path('test-pathao/', views.Test_pathao.as_view(), name='test-pathao'),
    path('get-stores/', views.GetStoresView.as_view(), name='get-stores'),
    path('create-store/', views.CreateStoreView.as_view(), name='create-store'),
    path('calculate-delivery-charge/', views.CalculateDeliveryChargeView.as_view(), name='calculate-delivery-charge'),
]
