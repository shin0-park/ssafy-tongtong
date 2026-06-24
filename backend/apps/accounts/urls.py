from django.urls import path

from apps.accounts.views import (
    LoginAPIView,
    LogoutAPIView,
    MeAPIView,
    SignupAPIView,
    TokenRefreshAPIView,
)


urlpatterns = [
    path("auth/signup/", SignupAPIView.as_view(), name="auth-signup"),
    path("auth/login/", LoginAPIView.as_view(), name="auth-login"),
    path("auth/token/refresh/", TokenRefreshAPIView.as_view(), name="auth-token-refresh"),
    path("auth/logout/", LogoutAPIView.as_view(), name="auth-logout"),
    path("users/me/", MeAPIView.as_view(), name="users-me"),
]
