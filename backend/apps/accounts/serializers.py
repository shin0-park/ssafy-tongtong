from django.contrib.auth import authenticate, get_user_model
from django.contrib.auth.password_validation import validate_password
from django.db import transaction
from rest_framework import serializers

from apps.accounts.models import UserProfile
from apps.preferences.models import UserPreference


User = get_user_model()


class UserSerializer(serializers.ModelSerializer):
    class Meta:
        model = User
        fields = ("id", "email", "nickname")
        read_only_fields = fields


class SignupSerializer(serializers.Serializer):
    email = serializers.EmailField()
    nickname = serializers.CharField(max_length=50)
    password = serializers.CharField(write_only=True, trim_whitespace=False)

    def validate_email(self, value):
        if User.objects.filter(email__iexact=value).exists():
            raise serializers.ValidationError("A user with this email already exists.")
        return value

    def validate_password(self, value):
        validate_password(value)
        return value

    @transaction.atomic
    def create(self, validated_data):
        user = User.objects.create_user(
            email=validated_data["email"],
            password=validated_data["password"],
            nickname=validated_data["nickname"],
        )
        UserProfile.objects.get_or_create(user=user)
        UserPreference.objects.get_or_create(user=user)
        return user


class LoginSerializer(serializers.Serializer):
    email = serializers.EmailField()
    password = serializers.CharField(write_only=True, trim_whitespace=False)

    def validate(self, attrs):
        user = authenticate(
            request=self.context.get("request"),
            username=attrs["email"],
            password=attrs["password"],
        )
        if user is None:
            raise serializers.ValidationError("Unable to log in with provided credentials.")
        if not user.is_active:
            raise serializers.ValidationError("User account is disabled.")
        attrs["user"] = user
        return attrs


class MeUpdateSerializer(serializers.ModelSerializer):
    class Meta:
        model = User
        fields = ("id", "email", "nickname")
        read_only_fields = ("id", "email")
