from rest_framework import generics, status
from rest_framework.response import Response
from rest_framework.permissions import IsAdminUser
from apps.accounts.models import User, CustomerProfile
from apps.accounts.serializers import UserSerializer
from apps.products.models import Category
from apps.vendor.models import VendorProfile
from .services.dashboard_service import get_dashboard_data
from .serializers import AdminCustomerSerializer, AdminCategorySerializer, AdminVendorSerializer
from .paginations import AdminCustomerListPaginataion, AdminCategoryListPagination, AdminVendorListPagination
from django.db.models import Q

class DashboardDataView(generics.GenericAPIView):
    permission_classes = [IsAdminUser]

    def get(self, request, *args, **kwargs):
        data = get_dashboard_data()
        return Response(data)

class UserListView(generics.ListAPIView):
    queryset = User.objects.all()
    serializer_class = UserSerializer
    permission_classes = [IsAdminUser]

class CustomerListView(generics.ListAPIView):
    serializer_class = AdminCustomerSerializer
    permission_classes = [IsAdminUser]
    pagination_class = AdminCustomerListPaginataion

    def get_queryset(self):
        quesry = self.request.query_params.get('search', None)
        filter = self.request.query_params.get('filter', None)
        query_set = CustomerProfile.objects.select_related('user').all()
        if quesry:
            query_set = query_set.filter(
                Q(user__full_name=quesry) |
                Q(user__email__icontains=quesry)
            )
        if filter == 'active':
            query_set = query_set.filter(user__is_active=True)
        elif filter == 'inactive':
            query_set = query_set.filter(user__is_active=False)

        return query_set

class VendorListView(generics.ListAPIView):
    serializer_class = AdminVendorSerializer
    permission_classes = [IsAdminUser]
    pagination_class = AdminVendorListPagination

    def get_queryset(self):
        quesry = self.request.query_params.get('search', None)
        filter = self.request.query_params.get('filter', None)
        query_set = VendorProfile.objects.select_related('user').all()
        status_choices = dict(VendorProfile.VerificationStatus.choices)
        if quesry:
            query_set = query_set.filter(
                Q(user__full_name=quesry) |
                Q(user__email__icontains=quesry)
            )
        if filter in status_choices:
            query_set = query_set.filter(verification_status=filter)


        return query_set

        
class AdminCategoryListView(generics.ListCreateAPIView):
    queryset = Category.objects.all()
    serializer_class = AdminCategorySerializer
    permission_classes = [IsAdminUser]
    # pagination_class = AdminCategoryListPagination
