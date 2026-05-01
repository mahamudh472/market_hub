from django.urls import path
from . import views

urlpatterns = [
    path('', views.DashboardDataView.as_view()),
    path('customers/', views.CustomerListView.as_view()),
    path('vendors/', views.VendorListView.as_view()),
    path('categories/', views.AdminCategoryListView.as_view())
]
