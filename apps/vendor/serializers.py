from rest_framework import serializers
from .models import VendorProfile
from apps.products.models import Category, Product, ProductImage, ProductVariantType, ProductVariantOption, ProductVariant


class SimpleVendorProfileSerializer(serializers.ModelSerializer):
    """Lightweight vendor payload for list/summary views."""
    class Meta:
        model = VendorProfile
        fields = [
            'id', 'name', 'slug', 'logo',
            'city', 'country',
            'avg_rating', 'total_reviews',
            'is_verified', 'verification_status',
        ]


class VendorProfileSerializer(SimpleVendorProfileSerializer):
    """Backward-compatible alias for existing imports."""


class VendorDetailSerializer(serializers.ModelSerializer):
    """Full store detail page data."""
    can_resubmit = serializers.SerializerMethodField()
    has_submitted_before = serializers.SerializerMethodField()

    class Meta:
        model = VendorProfile
        fields = [
            'id', 'name', 'slug', 'description',
            'logo', 'banner_image',
            'contact_email', 'contact_phone',
            'secondary_phone', 'otp_number',
            'address', 'city', 'zone', 'area', 'country',
            'avg_rating', 'total_reviews',
            'is_verified',
            'verification_status',
            'last_submitted_at',
            'has_submitted_before',
            'can_resubmit',
            'profile_completed',
            'created_at', 'updated_at',
        ]

    def get_can_resubmit(self, obj):
        return obj.verification_status != VendorProfile.VerificationStatus.BLOCKED

    def get_has_submitted_before(self, obj):
        return obj.last_submitted_at is not None


class VendorProfileSubmissionSerializer(serializers.ModelSerializer):
    class Meta:
        model = VendorProfile
        fields = [
            'name',
            'description',
            'logo',
            'banner_image',
            'contact_email',
            'contact_phone',
            'secondary_phone',
            'otp_number',
            'address',
            'city',
            'zone',
            'area',
            'country',
        ]

    def validate(self, attrs):
        city = attrs.get('city', getattr(self.instance, 'city', None))
        zone = attrs.get('zone', getattr(self.instance, 'zone', None))
        area = attrs.get('area', getattr(self.instance, 'area', None))

        if city and zone and zone.city_id != city.city_id:
            raise serializers.ValidationError({'zone': 'Selected zone does not belong to the selected city.'})
        if zone and area and area.zone_id != zone.zone_id:
            raise serializers.ValidationError({'area': 'Selected area does not belong to the selected zone.'})

        return attrs


class ProductVariantOptionSerializer(serializers.Serializer):
    value = serializers.CharField(max_length=100)


class ProductVariantTypeSerializer(serializers.Serializer):
    name = serializers.CharField(max_length=100)          # e.g. "Size", "Color"
    options = ProductVariantOptionSerializer(many=True)   # e.g. ["SM","M","XL"]


class ProductVariantSerializer(serializers.Serializer):
    """
    Maps a combination of option values to a price / stock / image.

    'options' is a list of (variant_type_name, option_value) pairs so the
    client can reference options by the names it already sent in variant_types.

    Example payload:
        {
            "options": [
                {"type": "Size",  "value": "SM"},
                {"type": "Color", "value": "Red"}
            ],
            "price":    10.00,
            "discount": 5.00,
            "stock":    50,
            "image":    <file>   # optional
        }
    """
    class VariantOptionRefSerializer(serializers.Serializer):
        type  = serializers.CharField()   # must match a name in variant_types
        value = serializers.CharField()   # must match an option value in that type

    options  = VariantOptionRefSerializer(many=True)
    price    = serializers.DecimalField(max_digits=10, decimal_places=2)
    discount = serializers.DecimalField(
        max_digits=5, decimal_places=2, required=False, allow_null=True
    )
    stock    = serializers.IntegerField(min_value=0)
    image    = serializers.ImageField(required=False, allow_null=True)


class ProductImageSerializer(serializers.Serializer):
    image     = serializers.ImageField()
    thumbnail = serializers.BooleanField(default=False)

class ProductCreateSerializer(serializers.ModelSerializer):
    images        = ProductImageSerializer(many=True, required=False)
    variant_types = ProductVariantTypeSerializer(many=True, required=False)
    variants      = ProductVariantSerializer(many=True, required=False)

    class Meta:
        model  = Product
        fields = [
            "name", "description", "price", "discount",
            "stock", "category", "product_details", "return_policy",
            "images", "variant_types", "variants",
        ]

    def validate(self, attrs):
        variant_types = attrs.get("variant_types", [])
        variants      = attrs.get("variants", [])

        if variants and not variant_types:
            raise serializers.ValidationError(
                "You must provide 'variant_types' when sending 'variants'."
            )

        if variants:
            # Build a lookup: type_name → set of valid option values
            valid: dict[str, set] = {
                vt["name"]: {o["value"] for o in vt["options"]}
                for vt in variant_types
            }

            for idx, variant in enumerate(variants):
                for ref in variant["options"]:
                    t, v = ref["type"], ref["value"]
                    if t not in valid:
                        raise serializers.ValidationError(
                            f"variants[{idx}]: unknown variant type '{t}'."
                        )
                    if v not in valid[t]:
                        raise serializers.ValidationError(
                            f"variants[{idx}]: '{v}' is not a valid option for '{t}'."
                        )

        return attrs

    def create(self, validated_data):
        images_data        = validated_data.pop("images", [])
        variant_types_data = validated_data.pop("variant_types", [])
        variants_data      = validated_data.pop("variants", [])

        product = Product.objects.create(**validated_data)

        # 2. Images
        ProductImage.objects.bulk_create([
            ProductImage(product=product, **img) for img in images_data
        ])

        # 3. Variant types + options
        #    Build a nested lookup so we can resolve options later:
        #    option_map["Size"]["SM"] → ProductVariantOption instance
        option_map: dict[str, dict[str, ProductVariantOption]] = {}

        for vt_data in variant_types_data:
            vt = ProductVariantType.objects.create(
                product=product, name=vt_data["name"]
            )
            option_map[vt.name] = {}
            for opt_data in vt_data["options"]:
                opt = ProductVariantOption.objects.create(
                    variant_type=vt, value=opt_data["value"]
                )
                option_map[vt.name][opt.value] = opt

        # 4. Variants
        for v_data in variants_data:
            option_refs = v_data.pop("options")
            variant = ProductVariant.objects.create(product=product, **v_data)
            variant.options.set([
                option_map[ref["type"]][ref["value"]] for ref in option_refs
            ])

        return product
