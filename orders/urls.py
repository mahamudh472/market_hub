from django.urls import path
from . import views
from .utils.ssl_commerz_util import payment_success, payment_fail, payment_cancel, payment_ipn

urlpatterns = [
    path('', views.OrderListView.as_view(), name='order-list'),
    path('checkout/', views.CheckoutView.as_view(), name='order-checkout'),
    path('<uuid:pk>/', views.OrderDetailView.as_view(), name='order-detail'),
    path('pathao/cities/', views.PathaoCityListView.as_view(), name='pathao-city-list'),
    path('pathao/zones/', views.PathaoZoneListView.as_view(), name='pathao-zone-list'),
    path('pathao/areas/', views.PathaoAreaListView.as_view(), name='pathao-area-list'),
    path('test-pathao/', views.Test_pathao.as_view(), name='test-pathao'),
    path('get-stores/', views.GetStoresView.as_view(), name='get-stores'),
    path('create-store/', views.CreateStoreView.as_view(), name='create-store'),
    path('calculate-delivery-charge/', views.CalculateDeliveryChargeView.as_view(), name='calculate-delivery-charge'),

    path('payment/', views.SslCommerzPaymentView.as_view(), name='payment'),
    path("payment/success/", payment_success),
    path("payment/fail/", payment_fail),
    path("payment/cancel/", payment_cancel),
    path("payment/ipn/", payment_ipn),
]
