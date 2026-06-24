from django.db.models import Prefetch
from django.shortcuts import get_object_or_404
from rest_framework import status
from rest_framework.generics import ListAPIView
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from apps.books.models import Book
from apps.common.pagination import StandardPageNumberPagination
from apps.community.models import (
    ReviewBookReference,
    ReviewModerationStatus,
    ReviewProgramReference,
    ReviewTag,
    UserReview,
    UserReviewImage,
    UserReviewLike,
)
from apps.community.serializers import UserReviewSerializer
from apps.libraries.models import Library
from apps.myoutings.models import UserBookSave, UserLibrarySave, UserProgramSave
from apps.myoutings.serializers import (
    LikedReviewSerializer,
    UserBookSaveSerializer,
    UserLibrarySaveSerializer,
    UserProgramSaveSerializer,
)
from apps.myoutings.services import build_my_outings_dashboard
from apps.programs.models import Program


def review_prefetches(prefix=""):
    return (
        Prefetch(
            f"{prefix}tag_links",
            queryset=ReviewTag.objects.select_related("tag").order_by("created_at", "id"),
            to_attr="prefetched_tag_links",
        ),
        Prefetch(
            f"{prefix}book_references",
            queryset=ReviewBookReference.objects.select_related("book").order_by("display_order", "id"),
            to_attr="prefetched_book_references",
        ),
        Prefetch(
            f"{prefix}program_references",
            queryset=ReviewProgramReference.objects.select_related("program__library").order_by("display_order", "id"),
            to_attr="prefetched_program_references",
        ),
        Prefetch(
            f"{prefix}images",
            queryset=UserReviewImage.objects.order_by("display_order", "id"),
            to_attr="prefetched_images",
        ),
    )


class BaseSaveAPIView(APIView):
    permission_classes = (IsAuthenticated,)
    target_type = None
    lookup_url_kwarg = None
    save_model = None
    save_field = None

    def get_target(self):
        raise NotImplementedError

    def get_response_target_id(self, target):
        return target.pk

    def build_response(self, target, saved):
        return {
            "saved": saved,
            "target_type": self.target_type,
            "target_id": self.get_response_target_id(target),
        }

    def post(self, request, *args, **kwargs):
        target = self.get_target()
        _, created = self.save_model.objects.get_or_create(
            user=request.user,
            **{self.save_field: target},
        )
        response_status = status.HTTP_201_CREATED if created else status.HTTP_200_OK
        return Response(self.build_response(target, True), status=response_status)

    def delete(self, request, *args, **kwargs):
        target = self.get_target()
        self.save_model.objects.filter(
            user=request.user,
            **{self.save_field: target},
        ).delete()
        return Response(self.build_response(target, False), status=status.HTTP_200_OK)


class LibrarySaveAPIView(BaseSaveAPIView):
    target_type = "library"
    lookup_url_kwarg = "library_id"
    save_model = UserLibrarySave
    save_field = "library"

    def get_target(self):
        return get_object_or_404(
            Library.objects.filter(is_active=True),
            pk=self.kwargs[self.lookup_url_kwarg],
        )


class BookSaveAPIView(BaseSaveAPIView):
    target_type = "book"
    lookup_url_kwarg = "isbn13"
    save_model = UserBookSave
    save_field = "book"

    def get_target(self):
        return get_object_or_404(
            Book.objects.filter(is_active=True),
            isbn13=self.kwargs[self.lookup_url_kwarg],
        )

    def get_response_target_id(self, target):
        return target.isbn13


class ProgramSaveAPIView(BaseSaveAPIView):
    target_type = "program"
    lookup_url_kwarg = "program_id"
    save_model = UserProgramSave
    save_field = "program"

    def get_target(self):
        return get_object_or_404(
            Program.objects.filter(is_visible=True, deleted_at__isnull=True),
            pk=self.kwargs[self.lookup_url_kwarg],
        )


class MyOutingsDashboardAPIView(APIView):
    permission_classes = (IsAuthenticated,)

    def get(self, request, *args, **kwargs):
        return Response(build_my_outings_dashboard(request.user), status=status.HTTP_200_OK)


class SavedLibraryListAPIView(ListAPIView):
    serializer_class = UserLibrarySaveSerializer
    permission_classes = (IsAuthenticated,)
    pagination_class = StandardPageNumberPagination

    def get_queryset(self):
        return (
            UserLibrarySave.objects.filter(user=self.request.user, library__is_active=True)
            .select_related("library")
            .prefetch_related(
                "library__statistic_snapshots",
                "library__images__media_asset",
            )
            .order_by("-created_at", "-id")
        )


class SavedBookListAPIView(ListAPIView):
    serializer_class = UserBookSaveSerializer
    permission_classes = (IsAuthenticated,)
    pagination_class = StandardPageNumberPagination

    def get_queryset(self):
        return (
            UserBookSave.objects.filter(user=self.request.user, book__is_active=True)
            .select_related("book")
            .order_by("-created_at", "-id")
        )


class SavedProgramListAPIView(ListAPIView):
    serializer_class = UserProgramSaveSerializer
    permission_classes = (IsAuthenticated,)
    pagination_class = StandardPageNumberPagination

    def get_queryset(self):
        return (
            UserProgramSave.objects.filter(
                user=self.request.user,
                program__is_visible=True,
                program__deleted_at__isnull=True,
            )
            .select_related("program", "program__library")
            .order_by("-created_at", "-id")
        )


class MyReviewListAPIView(ListAPIView):
    serializer_class = UserReviewSerializer
    permission_classes = (IsAuthenticated,)
    pagination_class = StandardPageNumberPagination

    def get_queryset(self):
        return (
            UserReview.objects.filter(user=self.request.user)
            .select_related("user", "library")
            .prefetch_related(*review_prefetches())
            .order_by("-created_at", "-id")
        )


class LikedReviewListAPIView(ListAPIView):
    serializer_class = LikedReviewSerializer
    permission_classes = (IsAuthenticated,)
    pagination_class = StandardPageNumberPagination

    def get_queryset(self):
        return (
            UserReviewLike.objects.filter(
                user=self.request.user,
                review__moderation_status=ReviewModerationStatus.VISIBLE,
            )
            .select_related("review", "review__user", "review__library")
            .prefetch_related(*review_prefetches("review__"))
            .order_by("-created_at", "-id")
        )
