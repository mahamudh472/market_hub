from django.urls import path
from . import views

urlpatterns = [
    path('', views.CartDetailView.as_view(), name='cart-detail'),
    path('items/', views.CartItemAddView.as_view(), name='cart-item-add'),
    path('items/<int:item_id>/', views.CartItemUpdateView.as_view(), name='cart-item-update'),
    path('items/<int:item_id>/delete/', views.CartItemDeleteView.as_view(), name='cart-item-delete'),
    path('clear/', views.CartClearView.as_view(), name='cart-clear'),
    path('voucher/apply/', views.ApplyVoucherView.as_view(), name='cart-voucher-apply'),
    path('voucher/remove/', views.RemoveVoucherView.as_view(), name='cart-voucher-remove'),
]
