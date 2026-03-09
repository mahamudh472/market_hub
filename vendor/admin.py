from django.contrib import admin
from unfold.admin import ModelAdmin
from .models import VendorProfile


@admin.register(VendorProfile)
class VendorProfileAdmin(ModelAdmin):
    list_display = ['name', 'user', 'city', 'is_verified', 'is_active', 'avg_rating', 'created_at']
    list_filter = ['is_verified', 'is_active', 'country']
    search_fields = ['name', 'user__email', 'city']
    raw_id_fields = ['user']
    list_fullwidth = True
