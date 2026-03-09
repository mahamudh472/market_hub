from django.contrib import admin
from unfold.admin import ModelAdmin, TabularInline, StackedInline
from .models import Cart, CartItem, Voucher, VoucherUsage


@admin.register(Voucher)
class VoucherAdmin(ModelAdmin):
    list_display = ['code', 'discount_type', 'discount_value', 'is_active', 'valid_from', 'valid_until']
    search_fields = ['code']
    list_filter = ['discount_type', 'is_active']


@admin.register(VoucherUsage)
class VoucherUsageAdmin(ModelAdmin):
    list_display = ['voucher', 'user', 'used_at']
    raw_id_fields = ['voucher', 'user']


class CartItemInline(TabularInline):
    model = CartItem
    extra = 0
    raw_id_fields = ['product', 'variant']
    tab = True


@admin.register(Cart)
class CartAdmin(ModelAdmin):
    list_display = ['user', 'voucher', 'created_at', 'updated_at']
    raw_id_fields = ['user', 'voucher']
    inlines = [CartItemInline]
