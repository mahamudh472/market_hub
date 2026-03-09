from rest_framework import serializers
from .models import (
    Product, ProductImage, Category,
    ProductVariantType, ProductVariantOption, ProductVariant,
    ProductReview, ProductReviewImage,
)


# ─────────────────────────────────────────
# Category
# ─────────────────────────────────────────
class CategorySerializer(serializers.ModelSerializer):
    product_count = serializers.IntegerField(read_only=True)

    class Meta:
        model = Category
        fields = ['id', 'name', 'slug', 'image', 'product_count']


class CategoryDetailSerializer(serializers.ModelSerializer):
    """Category with nested child categories"""
    children = serializers.SerializerMethodField()
    product_count = serializers.IntegerField(read_only=True)

    class Meta:
        model = Category
        fields = ['id', 'name', 'slug', 'image', 'parent', 'children', 'product_count']

    def get_children(self, obj):
        children = obj.category_set.all() if hasattr(obj, 'category_set') else []
        return CategorySerializer(children, many=True, context=self.context).data


# ─────────────────────────────────────────
# Product Image
# ─────────────────────────────────────────
class ProductImageSerializer(serializers.ModelSerializer):
    class Meta:
        model = ProductImage
        fields = ['id', 'image', 'thumbnail']


# ─────────────────────────────────────────
# Variant
# ─────────────────────────────────────────
class ProductVariantOptionSerializer(serializers.ModelSerializer):
    variant_type_name = serializers.CharField(source='variant_type.name', read_only=True)

    class Meta:
        model = ProductVariantOption
        fields = ['id', 'variant_type_name', 'value']


class ProductVariantTypeSerializer(serializers.ModelSerializer):
    options = ProductVariantOptionSerializer(many=True, read_only=True)

    class Meta:
        model = ProductVariantType
        fields = ['id', 'name', 'options']


class ProductVariantSerializer(serializers.ModelSerializer):
    options = ProductVariantOptionSerializer(many=True, read_only=True)

    class Meta:
        model = ProductVariant
        fields = ['id', 'options', 'price', 'discount', 'discounted_price', 'stock', 'image']


# ─────────────────────────────────────────
# Review
# ─────────────────────────────────────────
class ProductReviewImageSerializer(serializers.ModelSerializer):
    class Meta:
        model = ProductReviewImage
        fields = ['id', 'image']


class ProductReviewSerializer(serializers.ModelSerializer):
    images = ProductReviewImageSerializer(many=True, read_only=True)
    user_name = serializers.CharField(source='user.full_name', read_only=True)
    user_avatar = serializers.ImageField(source='user.avatar', read_only=True)
    uploaded_images = serializers.ListField(
        child=serializers.ImageField(), write_only=True, required=False
    )

    class Meta:
        model = ProductReview
        fields = [
            'id', 'user_name', 'user_avatar',
            'rating', 'comment', 'images',
            'uploaded_images', 'created_at',
        ]
        read_only_fields = ['id', 'user_name', 'user_avatar', 'images', 'created_at']

    def validate_rating(self, value):
        if not 1 <= value <= 5:
            raise serializers.ValidationError("Rating must be between 1 and 5.")
        return value

    def create(self, validated_data):
        uploaded_images = validated_data.pop('uploaded_images', [])
        review = ProductReview.objects.create(**validated_data)
        for img in uploaded_images:
            ProductReviewImage.objects.create(review=review, image=img)
        return review


# ─────────────────────────────────────────
# Simple product card (used in lists)
# ─────────────────────────────────────────
class SimpleProductSerializer(serializers.ModelSerializer):
    vendor_name = serializers.CharField(source='vendor.name', read_only=True)
    vendor_id = serializers.IntegerField(source='vendor.id', read_only=True)
    thumbnail = serializers.SerializerMethodField()
    reviews_count = serializers.IntegerField(source='reviews.count', read_only=True)
    avg_rating = serializers.SerializerMethodField()
    category_name = serializers.CharField(source='category.name', read_only=True)
    is_wishlisted = serializers.SerializerMethodField()

    class Meta:
        model = Product
        fields = [
            'id', 'name', 'price', 'discount', 'discounted_price',
            'vendor_name', 'vendor_id', 'thumbnail',
            'reviews_count', 'avg_rating', 'category_name',
            'is_wishlisted',
        ]

    def get_thumbnail(self, obj):
        request = self.context.get('request')
        img_obj = obj.images.filter(thumbnail=True).first() or obj.images.first()
        if img_obj:
            url = img_obj.image.url
            return request.build_absolute_uri(url) if request else url
        return None

    def get_avg_rating(self, obj):
        reviews = obj.reviews.all()
        if not reviews.exists():
            return None
        return round(sum(r.rating for r in reviews) / reviews.count(), 1)

    def get_is_wishlisted(self, obj):
        request = self.context.get('request')
        if request and request.user.is_authenticated:
            return obj.wishlisted_by.filter(user=request.user).exists()
        return False


# ─────────────────────────────────────────
# Full Product detail
# ─────────────────────────────────────────
class ProductSerializer(serializers.ModelSerializer):
    images = ProductImageSerializer(many=True, read_only=True)
    category = CategorySerializer(read_only=True)
    category_id = serializers.PrimaryKeyRelatedField(
        queryset=Category.objects.all(), source='category', write_only=True
    )
    variant_types = ProductVariantTypeSerializer(many=True, read_only=True)
    variants = ProductVariantSerializer(many=True, read_only=True)
    vendor_name = serializers.CharField(source='vendor.name', read_only=True)
    vendor_id = serializers.IntegerField(source='vendor.id', read_only=True)
    vendor_slug = serializers.CharField(source='vendor.slug', read_only=True)
    reviews_count = serializers.IntegerField(source='reviews.count', read_only=True)
    avg_rating = serializers.SerializerMethodField()
    is_wishlisted = serializers.SerializerMethodField()

    class Meta:
        model = Product
        fields = [
            'id', 'name', 'description', 'product_details', 'return_policy',
            'price', 'discount', 'discounted_price', 'stock',
            'category', 'category_id',
            'vendor_name', 'vendor_id', 'vendor_slug',
            'images', 'variant_types', 'variants',
            'reviews_count', 'avg_rating', 'is_wishlisted',
            'created_at',
        ]

    def get_avg_rating(self, obj):
        reviews = obj.reviews.all()
        if not reviews.exists():
            return None
        return round(sum(r.rating for r in reviews) / reviews.count(), 1)

    def get_is_wishlisted(self, obj):
        request = self.context.get('request')
        if request and request.user.is_authenticated:
            return obj.wishlisted_by.filter(user=request.user).exists()
        return False
