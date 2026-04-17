from django.contrib import admin
from unfold.admin import ModelAdmin
from .models import User, UserAddress, CustomerProfile


@admin.register(User)
class UserAdmin(ModelAdmin):
    list_display = ['email', 'full_name', 'is_active', 'is_staff', 'joined_at']
    search_fields = ['email', 'full_name']
    list_filter = ['is_active', 'is_staff']
    ordering = ['email']
    list_fullwidth = True


@admin.register(UserAddress)
class UserAddressAdmin(ModelAdmin):
    list_display = ['user', 'label', 'city', 'country', 'is_default_delivery']
    list_filter = ['label', 'country', 'is_default_delivery']
    search_fields = ['user__email', 'city']
    raw_id_fields = ['user']

@admin.register(CustomerProfile)
class CustomerProfileAdmin(ModelAdmin):
    list_display = ['user']
    search_fields = ['user__email', 'user__full_name']
    raw_id_fields = ['user']
