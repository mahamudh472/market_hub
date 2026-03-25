from rest_framework import generics
from rest_framework.permissions import IsAdminUser
from accounts.models import User
from accounts.serializers import UserSerializer

class UserListView(generics.ListAPIView):
    queryset = User.objects.all()
    serializer_class = UserSerializer
    permission_classes = [IsAdminUser]

