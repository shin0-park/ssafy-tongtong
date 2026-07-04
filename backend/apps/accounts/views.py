from django.conf import settings
from django.contrib.auth import get_user_model
from rest_framework import status
from rest_framework.parsers import FormParser, JSONParser, MultiPartParser
from rest_framework.permissions import AllowAny, IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView
from rest_framework_simplejwt.exceptions import TokenError
from rest_framework_simplejwt.settings import api_settings
from rest_framework_simplejwt.tokens import RefreshToken

from apps.accounts.serializers import (
    LoginSerializer,
    MeUpdateSerializer,
    SignupSerializer,
    UserPreferencesSerializer,
    UserPreferencesUpdateSerializer,
    UserSerializer,
)


User = get_user_model()


def _set_refresh_cookie(response, refresh_token):
    response.set_cookie(
        settings.JWT_REFRESH_COOKIE_NAME,
        str(refresh_token),
        max_age=settings.JWT_REFRESH_COOKIE_MAX_AGE,
        httponly=settings.JWT_REFRESH_COOKIE_HTTPONLY,
        secure=settings.JWT_REFRESH_COOKIE_SECURE,
        samesite=settings.JWT_REFRESH_COOKIE_SAMESITE,
        path=settings.JWT_REFRESH_COOKIE_PATH,
    )


def _delete_refresh_cookie(response):
    response.delete_cookie(
        settings.JWT_REFRESH_COOKIE_NAME,
        path=settings.JWT_REFRESH_COOKIE_PATH,
        samesite=settings.JWT_REFRESH_COOKIE_SAMESITE,
    )


def _token_response(user, response_status=status.HTTP_200_OK):
    refresh = RefreshToken.for_user(user)
    response = Response(
        {
            "user": UserSerializer(user).data,
            "access": str(refresh.access_token),
        },
        status=response_status,
    )
    # refresh token은 JS에서 읽지 못하는 cookie로만 내려 access token 재발급에 사용한다.
    _set_refresh_cookie(response, refresh)
    return response


class SignupAPIView(APIView):
    permission_classes = (AllowAny,)

    def post(self, request):
        serializer = SignupSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        user = serializer.save()
        return _token_response(user, status.HTTP_201_CREATED)


class LoginAPIView(APIView):
    permission_classes = (AllowAny,)

    def post(self, request):
        serializer = LoginSerializer(data=request.data, context={"request": request})
        serializer.is_valid(raise_exception=True)
        return _token_response(serializer.validated_data["user"])


class TokenRefreshAPIView(APIView):
    permission_classes = (AllowAny,)

    def post(self, request):
        raw_refresh = request.COOKIES.get(settings.JWT_REFRESH_COOKIE_NAME)
        if not raw_refresh:
            return Response(
                {"detail": "Refresh token is missing."},
                status=status.HTTP_401_UNAUTHORIZED,
            )

        try:
            refresh = RefreshToken(raw_refresh)
            user_id = refresh[api_settings.USER_ID_CLAIM]
        except (KeyError, TokenError):
            return Response(
                {"detail": "Refresh token is invalid."},
                status=status.HTTP_401_UNAUTHORIZED,
            )

        if not User.objects.filter(pk=user_id, is_active=True).exists():
            return Response(
                {"detail": "Refresh token is invalid."},
                status=status.HTTP_401_UNAUTHORIZED,
            )

        return Response({"access": str(refresh.access_token)})


class LogoutAPIView(APIView):
    permission_classes = (AllowAny,)

    def post(self, request):
        response = Response({"detail": "Successfully logged out."})
        _delete_refresh_cookie(response)
        return response


class MeAPIView(APIView):
    permission_classes = (IsAuthenticated,)
    parser_classes = (JSONParser, MultiPartParser, FormParser)

    def get(self, request):
        return Response(UserSerializer(request.user).data)

    def patch(self, request):
        serializer = MeUpdateSerializer(
            request.user,
            data=request.data,
            partial=True,
        )
        serializer.is_valid(raise_exception=True)
        serializer.save()
        return Response(UserSerializer(request.user).data)


class MePreferencesAPIView(APIView):
    permission_classes = (IsAuthenticated,)

    def get(self, request):
        return Response(UserPreferencesSerializer(request.user).data)

    def put(self, request):
        serializer = UserPreferencesUpdateSerializer(
            data=request.data,
            context={"request": request},
        )
        serializer.is_valid(raise_exception=True)
        serializer.save()
        return Response(UserPreferencesSerializer(request.user).data)
