from django.urls import path
from . import views

urlpatterns = [
    path('home/', views.HomeAPIView.as_view(), name='home'),
    path('wishlist/', views.WishlistListView.as_view(), name='wishlist-list'),
    path('wishlist/<uuid:product_id>/toggle/', views.WishlistToggleView.as_view(), name='wishlist-toggle'),
    path('wishlist/<uuid:product_id>/', views.WishlistRemoveView.as_view(), name='wishlist-remove'),
]
