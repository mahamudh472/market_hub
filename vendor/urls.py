from django.urls import path
from . import views

urlpatterns = [
    path('stores/', views.StoreListView.as_view(), name="store-list"),
    path('store/', views.StoreDetailView.as_view(), name='store-detail'),
    path('store/<slug:slug>/', views.StoreDetailView.as_view(), name='store-detail'),
]
