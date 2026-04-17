from django.urls import path
from . import views

urlpatterns = [
    # Categories
    path('categories/', views.CategoryListView.as_view(), name='category-list'),
    path('categories/<slug:slug>/', views.CategoryProductListView.as_view(), name='category-products'),

    # Product listing / search
    path('', views.PopularProductListView.as_view(), name='product-list'),
    path('search/', views.ProductSearchView.as_view(), name='product-search'),

    # Product detail
    path('<uuid:pk>/', views.ProductDetailView.as_view(), name='product-detail'),

    # Reviews (separate, paginated)
    path('<uuid:product_id>/reviews/', views.ProductReviewListView.as_view(), name='product-reviews'),
    path('<uuid:product_id>/reviews/add/', views.ProductReviewCreateView.as_view(), name='product-review-add'),
]
