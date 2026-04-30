from django.contrib import admin
from unfold.admin import ModelAdmin, TabularInline
from .models import (
    Product, ProductImage, Category,
    ProductVariantType, ProductVariantOption, ProductVariant,
    ProductReview, ProductReviewImage,
)


@admin.register(Category)
class CategoryAdmin(ModelAdmin):
    list_display = ['name', 'slug', 'parent']
    search_fields = ['name']


class ProductImageInline(TabularInline):
    model = ProductImage
    extra = 1
    tab = True


class ProductVariantTypeInline(TabularInline):
    model = ProductVariantType
    extra = 0
    tab = True


@admin.register(Product)
class ProductAdmin(ModelAdmin):
    list_display = ['name', 'vendor', 'price', 'discount', 'stock', 'category', 'created_at']
    search_fields = ['name', 'vendor__name', 'category__name']
    list_filter = ['category', 'created_at']
    raw_id_fields = ['vendor']
    inlines = [ProductImageInline, ProductVariantTypeInline]
    list_fullwidth = True
    warn_unsaved_form = True


@admin.register(ProductVariant)
class ProductVariantAdmin(ModelAdmin):
    list_display = ['product', 'price', 'discount', 'stock']
    filter_horizontal = ['options']
    raw_id_fields = ['product']


@admin.register(ProductReview)
class ProductReviewAdmin(ModelAdmin):
    list_display = ['product', 'user', 'rating', 'created_at']
    search_fields = ['product__name', 'user__email']
    list_filter = ['rating', 'created_at']
    search_fields = ('review__product__name', 'review__user__username')


