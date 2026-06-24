from decimal import Decimal

from django.contrib.auth import authenticate, get_user_model
from django.contrib.auth.password_validation import validate_password
from django.db import transaction
from rest_framework import serializers

from apps.accounts.models import (
    UserPreferredPurpose,
    UserPreferredRegion,
    UserPreferredTag,
    UserProfile,
)
from apps.preferences.models import UserPreference
from apps.preferences.regions import (
    BUSAN_SIDO,
    BUSAN_SIGUNGU_SET,
    build_region_key,
)
from apps.recommendations.models import Purpose
from apps.tags.models import Tag


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


class PreferredPurposeSerializer(serializers.ModelSerializer):
    code = serializers.CharField(source="purpose.code")
    label = serializers.CharField(source="purpose.label")

    class Meta:
        model = UserPreferredPurpose
        fields = ("code", "label", "weight", "display_order")


class PreferredRegionSerializer(serializers.ModelSerializer):
    class Meta:
        model = UserPreferredRegion
        fields = ("region_key", "sido", "sigungu", "weight", "display_order")


class PreferredTagSerializer(serializers.ModelSerializer):
    code = serializers.CharField(source="tag.code")
    label = serializers.CharField(source="tag.label")

    class Meta:
        model = UserPreferredTag
        fields = ("code", "label", "weight", "display_order")


class UserPreferencesSerializer(serializers.Serializer):
    purposes = serializers.SerializerMethodField()
    regions = serializers.SerializerMethodField()
    tags = serializers.SerializerMethodField()

    def get_purposes(self, user):
        preferences = (
            user.preferred_purposes.filter(is_active=True)
            .select_related("purpose")
            .order_by("display_order", "id")
        )
        return PreferredPurposeSerializer(preferences, many=True).data

    def get_regions(self, user):
        preferences = user.preferred_regions.filter(is_active=True).order_by("display_order", "id")
        return PreferredRegionSerializer(preferences, many=True).data

    def get_tags(self, user):
        preferences = (
            user.preferred_tags.filter(is_active=True)
            .select_related("tag")
            .order_by("display_order", "id")
        )
        return PreferredTagSerializer(preferences, many=True).data


class PreferredRegionInputSerializer(serializers.Serializer):
    sido = serializers.CharField()
    sigungu = serializers.CharField()


class UserPreferencesUpdateSerializer(serializers.Serializer):
    purpose_codes = serializers.ListField(
        child=serializers.CharField(),
        allow_empty=True,
    )
    regions = serializers.ListField(
        child=PreferredRegionInputSerializer(),
        allow_empty=True,
    )
    tag_codes = serializers.ListField(
        child=serializers.CharField(),
        allow_empty=True,
    )

    def validate(self, attrs):
        attrs["purpose_codes"] = self.deduplicate(attrs["purpose_codes"])
        try:
            attrs["regions"] = self.validate_regions(attrs["regions"])
        except serializers.ValidationError as exc:
            raise serializers.ValidationError({"regions": exc.detail})
        attrs["tag_codes"] = self.deduplicate(attrs["tag_codes"])
        attrs["purposes"] = self.resolve_purposes(attrs["purpose_codes"])
        attrs["tags"] = self.resolve_tags(attrs["tag_codes"])
        return attrs

    @staticmethod
    def deduplicate(values):
        deduplicated = []
        seen = set()
        for value in values:
            if value in seen:
                continue
            seen.add(value)
            deduplicated.append(value)
        return deduplicated

    def validate_regions(self, regions):
        normalized_regions = []
        seen = set()
        for region in regions:
            sido = region["sido"].strip()
            sigungu = region["sigungu"].strip()
            if sido != BUSAN_SIDO or sigungu not in BUSAN_SIGUNGU_SET:
                raise serializers.ValidationError("Invalid Busan region.")

            region_key = build_region_key(sigungu)
            if region_key in seen:
                continue
            seen.add(region_key)
            normalized_regions.append(
                {
                    "region_key": region_key,
                    "sido": BUSAN_SIDO,
                    "sigungu": sigungu,
                }
            )
        return normalized_regions

    def resolve_purposes(self, purpose_codes):
        purposes = list(
            Purpose.objects.filter(
                code__in=purpose_codes,
                is_active=True,
                is_profile_selectable=True,
            )
        )
        found_codes = {purpose.code for purpose in purposes}
        invalid_codes = [code for code in purpose_codes if code not in found_codes]
        if invalid_codes:
            raise serializers.ValidationError({"purpose_codes": "Invalid purpose code."})
        return sorted(purposes, key=lambda purpose: purpose_codes.index(purpose.code))

    def resolve_tags(self, tag_codes):
        tags = list(
            Tag.objects.filter(
                code__in=tag_codes,
                is_active=True,
                is_profile_selectable=True,
            )
        )
        found_codes = {tag.code for tag in tags}
        invalid_codes = [code for code in tag_codes if code not in found_codes]
        if invalid_codes:
            raise serializers.ValidationError({"tag_codes": "Invalid tag code."})
        return sorted(tags, key=lambda tag: tag_codes.index(tag.code))

    @transaction.atomic
    def save(self, **kwargs):
        user = self.context["request"].user
        weight = Decimal("1.0000")

        UserPreferredPurpose.objects.filter(user=user, is_active=True).update(is_active=False)
        for display_order, purpose in enumerate(self.validated_data["purposes"]):
            UserPreferredPurpose.objects.update_or_create(
                user=user,
                purpose=purpose,
                defaults={
                    "weight": weight,
                    "display_order": display_order,
                    "is_active": True,
                },
            )

        UserPreferredRegion.objects.filter(user=user, is_active=True).update(is_active=False)
        for display_order, region in enumerate(self.validated_data["regions"]):
            UserPreferredRegion.objects.update_or_create(
                user=user,
                region_key=region["region_key"],
                defaults={
                    "sido": region["sido"],
                    "sigungu": region["sigungu"],
                    "weight": weight,
                    "display_order": display_order,
                    "is_active": True,
                },
            )

        UserPreferredTag.objects.filter(user=user, is_active=True).update(is_active=False)
        for display_order, tag in enumerate(self.validated_data["tags"]):
            UserPreferredTag.objects.update_or_create(
                user=user,
                tag=tag,
                defaults={
                    "weight": weight,
                    "display_order": display_order,
                    "is_active": True,
                },
            )

        return user
