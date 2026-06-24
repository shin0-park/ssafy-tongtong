from django.db.models import Prefetch, Q
from rest_framework import generics

from apps.common.pagination import StandardPageNumberPagination

from .models import (
    ReviewBookReference,
    ReviewModerationStatus,
    ReviewProgramReference,
    ReviewTag,
    UserReview,
    UserReviewImage,
)
from .serializers import UserReviewSerializer


class UserReviewQueryMixin:
    serializer_class = UserReviewSerializer

    def get_queryset(self):
        queryset = (
            UserReview.objects.filter(moderation_status=ReviewModerationStatus.VISIBLE)
            .select_related("user", "library")
            .prefetch_related(
                Prefetch(
                    "tag_links",
                    queryset=ReviewTag.objects.select_related("tag").order_by("created_at", "id"),
                    to_attr="prefetched_tag_links",
                ),
                Prefetch(
                    "book_references",
                    queryset=ReviewBookReference.objects.select_related("book").order_by("display_order", "id"),
                    to_attr="prefetched_book_references",
                ),
                Prefetch(
                    "program_references",
                    queryset=ReviewProgramReference.objects.select_related("program__library").order_by("display_order", "id"),
                    to_attr="prefetched_program_references",
                ),
                Prefetch(
                    "images",
                    queryset=UserReviewImage.objects.order_by("display_order", "id"),
                    to_attr="prefetched_images",
                ),
            )
        )
        return self.apply_filters(queryset).order_by(self.get_ordering(), "-id").distinct()

    def apply_filters(self, queryset):
        params = self.request.query_params

        query = params.get("q", "").strip()
        if query:
            queryset = queryset.filter(Q(content__icontains=query) | Q(library__name__icontains=query))

        library_id = params.get("library_id", "").strip()
        if library_id:
            queryset = queryset.filter(library_id=library_id)

        tag_values = self.split_query_values(params.get("tag"))
        if tag_values:
            queryset = queryset.filter(tag_links__tag__code__in=tag_values)

        user_id = params.get("user_id", "").strip()
        if user_id:
            queryset = queryset.filter(user_id=user_id)

        return queryset

    def get_ordering(self):
        ordering = self.request.query_params.get("ordering", "").strip()
        if ordering in {"-created_at", "-view_count", "-like_count"}:
            return ordering
        return "-created_at"

    @staticmethod
    def split_query_values(value):
        if not value:
            return []
        return [item.strip() for item in value.split(",") if item.strip()]


class UserReviewListAPIView(UserReviewQueryMixin, generics.ListAPIView):
    serializer_class = UserReviewSerializer
    pagination_class = StandardPageNumberPagination


class UserReviewDetailAPIView(UserReviewQueryMixin, generics.RetrieveAPIView):
    serializer_class = UserReviewSerializer
    lookup_url_kwarg = "review_id"
