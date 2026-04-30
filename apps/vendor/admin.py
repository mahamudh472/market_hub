from django import forms
from django.contrib import admin
from unfold.admin import ModelAdmin
from .models import VendorProfile
from django.urls import path
from django.http import JsonResponse
from apps.orders.models import PathaoCity, PathaoZone, PathaoArea


class VendorProfileForm(forms.ModelForm):
    class Meta:
        model = VendorProfile
        fields = '__all__'

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        instance = kwargs.get('instance')

        # Determine city/zone from POST data (form submission) or saved instance
        data = args[0] if args else None
        submitted_city_id = data.get('city') if data else None
        submitted_zone_id = data.get('zone') if data else None

        city_id = submitted_city_id or (instance.city_id if instance else None)
        zone_id = submitted_zone_id or (instance.zone_id if instance else None)

        # Zone: load options scoped to the active city; fallback to none
        if city_id:
            self.fields['zone'].queryset = PathaoZone.objects.filter(city_id=city_id)
        else:
            self.fields['zone'].queryset = PathaoZone.objects.none()

        # Area: load options scoped to the active zone; fallback to none
        if zone_id:
            self.fields['area'].queryset = PathaoArea.objects.filter(zone_id=zone_id)
        else:
            self.fields['area'].queryset = PathaoArea.objects.none()

        # Attach data attributes so JS knows which IDs are currently selected
        self.fields['zone'].widget.attrs.update({'data-city-id': city_id or ''})
        self.fields['area'].widget.attrs.update({'data-zone-id': zone_id or ''})


@admin.register(VendorProfile)
class VendorProfileAdmin(ModelAdmin):
    form = VendorProfileForm
    list_display = [
        'name',
        'user',
        'city',
        'verification_status',
        'is_verified',
        'is_active',
        'last_submitted_at',
        'avg_rating',
        'created_at',
    ]
    list_filter = ['verification_status', 'is_verified', 'is_active', 'country']
    search_fields = ['name', 'user__email', 'city']
    raw_id_fields = ['user']
    list_fullwidth = True

    class Media:
        js = ('vendor/js/vendor_location_dropdown.js',)

    def get_urls(self):
        urls = super().get_urls()
        custom_urls = [
            path('ajax/load-zones/', self.admin_site.admin_view(self.load_zones), name='ajax_load_zones'),
            path('ajax/load-areas/', self.admin_site.admin_view(self.load_areas), name='ajax_load_areas'),
        ]
        return custom_urls + urls

    def load_zones(self, request):
        city_id = request.GET.get('city_id')
        if city_id:
            zones = PathaoZone.objects.filter(city_id=city_id).values('zone_id', 'zone_name')
        else:
            zones = []
        return JsonResponse(list(zones), safe=False)

    def load_areas(self, request):
        zone_id = request.GET.get('zone_id')
        if zone_id:
            areas = PathaoArea.objects.filter(zone_id=zone_id).values('area_id', 'area_name')
        else:
            areas = []
        return JsonResponse(list(areas), safe=False)
