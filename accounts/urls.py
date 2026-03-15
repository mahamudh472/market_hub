from django.urls import path
from . import views
from rest_framework_simplejwt.views import (
    TokenRefreshView,
)


urlpatterns = [
    path('<str:user_type>/login/', views.CustomTokenObtainPairView.as_view(), name='login'),
    path('logout/', views.LogoutView.as_view(), name='logout'),
    path('token/refresh/', TokenRefreshView.as_view(), name='token_refresh'),
    path('<str:user_type>/register/', views.RegisterView.as_view(), name='register'),
    path('verify-email/', views.VerifyEmailView.as_view(), name='verify_email'),
    path('password-reset/', views.SendOTPView.as_view(), name='password_reset'),
    path('send-otp/', views.SendOTPView.as_view(), name='send_otp'),
    path('check-otp/', views.CheckOTPView.as_view(), name='check_otp'),
    path('password-reset-confirm/', views.PasswordResetConfirmView.as_view(), name='password_reset_confirm'),
    path('change-password/', views.ChangePasswordView.as_view(), name='change_password'),
    path('customer/profile/', views.ProfileView.as_view(), name='profile'),
    path('customer/profile/update/', views.UpdateProfileView.as_view(), name='profile_update'),
    path('vendor/profile/', views.ProfileView.as_view(), name='profile'),
    path('vendor/profile/update/', views.UpdateProfileView.as_view(), name='profile_update'),
]
