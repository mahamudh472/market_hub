from django.urls import path
from . import views

urlpatterns = [
    path('store/<slug:slug>/', views.StoreDetailView.as_view(), name='store-detail'),
]
