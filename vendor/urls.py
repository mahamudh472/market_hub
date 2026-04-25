from django.urls import path
from . import views
from products.views import VendorProductListView

urlpatterns = [
    path('stores/', views.StoreListView.as_view(), name="store-list"),
    path('store/', views.StoreDetailView.as_view(), name='store-detail'),
    path('store/<slug:slug>/', views.StoreDetailView.as_view(), name='store-detail'),

    # Vendor's own product list (paginated + search + category filter)
    path('products/', VendorProductListView.as_view(), name='vendor-products'),
    path('products/create/', views.VendorCreateProductView.as_view(), name='vendor-product-create'),

]
