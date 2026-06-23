from django.contrib.auth.base_user import BaseUserManager
from django.contrib.auth.models import AbstractUser
from django.conf import settings
from django.db import models

from apps.common.models import TimeStampedModel


class UserManager(BaseUserManager):
    use_in_migrations = True

    def _create_user(self, email, password, **extra_fields):
        if not email:
            raise ValueError("The Email must be set")
        email = self.normalize_email(email)
        user = self.model(email=email, **extra_fields)
        user.set_password(password)
        user.save(using=self._db)
        return user

    def create_user(self, email, password=None, **extra_fields):
        extra_fields.setdefault("is_staff", False)
        extra_fields.setdefault("is_superuser", False)
        return self._create_user(email, password, **extra_fields)

    def create_superuser(self, email, password=None, **extra_fields):
        extra_fields.setdefault("is_staff", True)
        extra_fields.setdefault("is_superuser", True)

        if extra_fields.get("is_staff") is not True:
            raise ValueError("Superuser must have is_staff=True.")
        if extra_fields.get("is_superuser") is not True:
            raise ValueError("Superuser must have is_superuser=True.")

        return self._create_user(email, password, **extra_fields)


class User(AbstractUser, TimeStampedModel):
    username = None
    email = models.EmailField(unique=True)
    nickname = models.CharField(max_length=50)

    USERNAME_FIELD = "email"
    REQUIRED_FIELDS = []

    objects = UserManager()

    def __str__(self):
        return self.nickname or self.email


class UserProfile(TimeStampedModel):
    user = models.OneToOneField("accounts.User", on_delete=models.CASCADE, related_name="profile")
    profile_image = models.ImageField(upload_to="profiles/", null=True, blank=True)
    profile_image_alt = models.CharField(max_length=200, blank=True)
    bio = models.CharField(max_length=300, blank=True)

    def __str__(self):
        return f"{self.user.email} profile"


class UserPreferredRegion(TimeStampedModel):
    user = models.ForeignKey("accounts.User", on_delete=models.CASCADE, related_name="preferred_regions")
    region_key = models.CharField(max_length=30)
    sido = models.CharField(max_length=40)
    sigungu = models.CharField(max_length=40, blank=True)
    weight = models.DecimalField(max_digits=5, decimal_places=4, default=1)
    display_order = models.PositiveSmallIntegerField(default=0)
    is_active = models.BooleanField(default=True, db_index=True)

    class Meta:
        constraints = [
            models.UniqueConstraint(fields=["user", "region_key"], name="uq_user_preferred_region")
        ]
        indexes = [
            models.Index(fields=["user", "is_active", "display_order"], name="idx_user_region_order")
        ]

    def __str__(self):
        return f"{self.user.email} {self.region_key}"


class UserPreferredTag(TimeStampedModel):
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="preferred_tags",
    )
    tag = models.ForeignKey(
        "tags.Tag",
        on_delete=models.PROTECT,
        related_name="preferred_by_users",
        help_text="Tag.is_profile_selectable=True 검증은 serializer/service에서 수행합니다.",
    )
    weight = models.DecimalField(max_digits=5, decimal_places=4, default=1)
    display_order = models.PositiveSmallIntegerField(default=0)
    is_active = models.BooleanField(default=True, db_index=True)

    class Meta:
        constraints = [
            models.UniqueConstraint(fields=["user", "tag"], name="uq_user_preferred_tag")
        ]
        indexes = [
            models.Index(fields=["user", "is_active", "display_order"], name="idx_user_tag_order")
        ]

    def __str__(self):
        return f"{self.user.email} {self.tag_id}"


class UserPreferredPurpose(TimeStampedModel):
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="preferred_purposes",
    )
    purpose = models.ForeignKey(
        "recommendations.Purpose",
        on_delete=models.PROTECT,
        related_name="preferred_by_users",
        help_text="Purpose.is_profile_selectable=True 검증은 serializer/service에서 수행합니다.",
    )
    weight = models.DecimalField(max_digits=5, decimal_places=4, default=1)
    display_order = models.PositiveSmallIntegerField(default=0)
    is_active = models.BooleanField(default=True, db_index=True)

    class Meta:
        constraints = [
            models.UniqueConstraint(
                fields=["user", "purpose"], name="uq_user_preferred_purpose"
            )
        ]
        indexes = [
            models.Index(
                fields=["user", "is_active", "display_order"],
                name="idx_user_purpose_order",
            )
        ]

    def __str__(self):
        return f"{self.user.email} {self.purpose_id}"
