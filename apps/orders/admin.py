from django.contrib import admin
from django.shortcuts import redirect
from django.urls import reverse
from unfold.admin import ModelAdmin, TabularInline, StackedInline
from .models import (
    Order,
    OrderItem,
    Payment,
    SubOrder,
    SiteSettings,
    PathaoCity,
    PathaoZone,
    PathaoArea,
    PathaoSyncProgress,
)


class OrderItemInline(TabularInline):
    model = OrderItem
    extra = 0
    raw_id_fields = ['product', 'variant', 'vendor']
    tab = True


class PaymentInline(StackedInline):
    model = Payment
    extra = 0
    tab = True


class SubOrderInline(TabularInline):
    model = SubOrder
    extra = 0
    raw_id_fields = ['vendor']
    tab = True


@admin.register(Order)
class OrderAdmin(ModelAdmin):
    list_display = ['order_number', 'user', 'status', 'total', 'delivery_charge', 'platform_fee', 'cod_charge', 'created_at']
    list_filter = ['status', 'created_at']
    search_fields = ['order_number', 'user__email']
    raw_id_fields = ['user', 'delivery_address']
    inlines = [SubOrderInline, OrderItemInline, PaymentInline]
    list_fullwidth = True
    warn_unsaved_form = True


@admin.register(Payment)
class PaymentAdmin(ModelAdmin):
    list_display = ['order', 'method', 'status', 'amount', 'paid_at']
    list_filter = ['method', 'status']
    search_fields = ['order__order_number', 'transaction_id']


@admin.register(SubOrder)
class SubOrderAdmin(ModelAdmin):
    list_display = ['id', 'parent_order', 'vendor', 'status', 'total', 'created_at']
    list_filter = ['status', 'created_at']
    search_fields = ['parent_order__order_number', 'vendor__name']
    raw_id_fields = ['parent_order', 'vendor']


@admin.register(SiteSettings)
class SiteSettingsAdmin(ModelAdmin):
    list_display = ['id', 'cod_fee', 'tax_percent', 'platform_fee', 'default_delivery_charge', 'updated_at']

    def changelist_view(self, request, extra_context=None):
        settings_obj = SiteSettings.objects.order_by('id').first()
        if settings_obj:
            url = reverse('admin:orders_sitesettings_change', args=[settings_obj.pk])
            return redirect(url)

        add_url = reverse('admin:orders_sitesettings_add')
        return redirect(add_url)

    def has_add_permission(self, request):
        if SiteSettings.objects.exists():
            return False
        return super().has_add_permission(request)

    def has_delete_permission(self, request, obj=None):
        return False


@admin.register(PathaoCity)
class PathaoCityAdmin(ModelAdmin):
    list_display = ['city_id', 'city_name']
    search_fields = ['city_name']


@admin.register(PathaoZone)
class PathaoZoneAdmin(ModelAdmin):
    list_display = ['zone_id', 'zone_name', 'city']
    list_filter = ['city']
    search_fields = ['zone_name', 'city__city_name']


@admin.register(PathaoArea)
class PathaoAreaAdmin(ModelAdmin):
    list_display = ['area_id', 'area_name', 'zone', 'home_delivery_available', 'pickup_available']
    list_filter = ['home_delivery_available', 'pickup_available', 'zone__city']
    search_fields = ['area_name', 'zone__zone_name', 'zone__city__city_name']


@admin.register(PathaoSyncProgress)
class PathaoSyncProgressAdmin(ModelAdmin):
    list_display = ['status', 'total_cities', 'last_synced_at']
    list_filter = ['status', 'last_synced_at']
    readonly_fields = [
        'last_synced_at',
        'total_cities',
        'cities',
        'synced_cities_ids',
        'synced_zones_ids',
        'synced_areas_ids',
        'status',
    ]
