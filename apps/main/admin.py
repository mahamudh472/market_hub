from django.contrib import admin
from unfold.admin import ModelAdmin
from .models import HomeBanner, Wishlist, DeliveryCharge


@admin.register(HomeBanner)
class HomeBannerAdmin(ModelAdmin):
    list_display = ['title', 'is_active', 'sort_order', 'created_at']
    search_fields = ['title']
    list_filter = ['is_active']


@admin.register(Wishlist)
class WishlistAdmin(ModelAdmin):
    list_display = ['user', 'product', 'added_at']
    raw_id_fields = ['user', 'product']


@admin.register(DeliveryCharge)
class DeliveryChargeAdmin(ModelAdmin):
    list_display = ['name', 'charge', 'min_order_amount', 'is_active']
