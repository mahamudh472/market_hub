from django.contrib import admin
from unfold.admin import ModelAdmin, TabularInline, StackedInline
from .models import Order, OrderItem, Payment


class OrderItemInline(TabularInline):
    model = OrderItem
    extra = 0
    raw_id_fields = ['product', 'variant', 'vendor']
    tab = True


class PaymentInline(StackedInline):
    model = Payment
    extra = 0
    tab = True


@admin.register(Order)
class OrderAdmin(ModelAdmin):
    list_display = ['order_number', 'user', 'status', 'total', 'created_at']
    list_filter = ['status', 'created_at']
    search_fields = ['order_number', 'user__email']
    raw_id_fields = ['user', 'delivery_address']
    inlines = [OrderItemInline, PaymentInline]
    list_fullwidth = True
    warn_unsaved_form = True


@admin.register(Payment)
class PaymentAdmin(ModelAdmin):
    list_display = ['order', 'method', 'status', 'amount', 'paid_at']
    list_filter = ['method', 'status']
    search_fields = ['order__order_number', 'transaction_id']
