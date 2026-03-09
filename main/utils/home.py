from django.db.models import Count, Avg

from main.serializers import HomeBannerSerializer
from products.serializers import CategorySerializer, SimpleProductSerializer
from products.models import Category, Product
from vendor.models import VendorProfile
from vendor.serializers import VendorProfileSerializer
from main.models import HomeBanner


def get_home_data(user=None, request=None):
    ctx = {"request": request}

    # ── Banners ──────────────────────────────────────────────
    banners = HomeBanner.objects.filter(is_active=True)
    banner_data = HomeBannerSerializer(banners, many=True, context=ctx).data

    # ── Top Categories (by product count) ────────────────────
    top_categories = (
        Category.objects
        .filter(parent__isnull=True)
        .annotate(product_count=Count('products'))
        .filter(product_count__gt=0)
        .order_by('-product_count')[:10]
    )
    top_category_data = CategorySerializer(top_categories, many=True, context=ctx).data

    # ── Popular Products (most reviewed) ─────────────────────
    popular_products = (
        Product.objects
        .annotate(review_count=Count('reviews'))
        .order_by('-review_count')
        .select_related('vendor', 'category')
        .prefetch_related('images', 'reviews')[:12]
    )
    popular_product_data = SimpleProductSerializer(popular_products, many=True, context=ctx).data

    # ── Best Offers (highest discount) ───────────────────────
    best_offers = (
        Product.objects
        .exclude(discount__isnull=True)
        .order_by('-discount')
        .select_related('vendor', 'category')
        .prefetch_related('images', 'reviews')[:12]
    )
    best_offer_data = SimpleProductSerializer(best_offers, many=True, context=ctx).data

    # ── Top Rated Products ────────────────────────────────────
    top_rated = (
        Product.objects
        .annotate(avg_rating=Avg('reviews__rating'), review_count=Count('reviews'))
        .filter(review_count__gte=1)
        .order_by('-avg_rating', '-review_count')
        .select_related('vendor', 'category')
        .prefetch_related('images', 'reviews')[:12]
    )
    top_rated_data = SimpleProductSerializer(top_rated, many=True, context=ctx).data

    # ── Top Stores ────────────────────────────────────────────
    top_stores = (
        VendorProfile.objects
        .filter(is_active=True)
        .annotate(product_count=Count('products'))
        .order_by('-avg_rating', '-product_count')[:6]
    )
    top_store_data = VendorProfileSerializer(top_stores, many=True, context=ctx).data

    return {
        'banners': banner_data,
        'top_categories': top_category_data,
        'popular_products': popular_product_data,
        'best_offers': best_offer_data,
        'top_rated': top_rated_data,
        'top_stores': top_store_data,
    }
