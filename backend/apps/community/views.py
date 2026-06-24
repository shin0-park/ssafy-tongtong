from django.db import transaction
from django.db.models import F, Prefetch, Q
from django.shortcuts import get_object_or_404
from rest_framework import generics
from rest_framework.exceptions import PermissionDenied
from rest_framework.parsers import FormParser, JSONParser, MultiPartParser
from rest_framework.permissions import IsAuthenticatedOrReadOnly
from rest_framework.response import Response
from rest_framework.views import APIView

from apps.common.pagination import StandardPageNumberPagination
from apps.preferences.services import schedule_user_preference_pending

from .models import (
    ReviewBookReference,
    ReviewModerationStatus,
    ReviewProgramReference,
    ReviewTag,
    UserReview,
    UserReviewImage,
    UserReviewLike,
)
from .serializers import UserReviewSerializer, UserReviewWriteSerializer


def review_response_queryset():
    return UserReview.objects.select_related("user", "library").prefetch_related(
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


class UserReviewQueryMixin:
    serializer_class = UserReviewSerializer

    def get_queryset(self):
        queryset = review_response_queryset().filter(moderation_status=ReviewModerationStatus.VISIBLE)
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


class UserReviewListAPIView(UserReviewQueryMixin, generics.ListCreateAPIView):
    serializer_class = UserReviewSerializer
    pagination_class = StandardPageNumberPagination
    permission_classes = (IsAuthenticatedOrReadOnly,)
    parser_classes = (JSONParser, MultiPartParser, FormParser)

    @transaction.atomic
    def create(self, request, *args, **kwargs):
        serializer = UserReviewWriteSerializer(data=request.data, context={"request": request})
        serializer.is_valid(raise_exception=True)
        review = serializer.save()
        schedule_user_preference_pending(request.user)
        review = review_response_queryset().get(pk=review.pk)
        return Response(UserReviewSerializer(review).data, status=201)


class UserReviewDetailAPIView(UserReviewQueryMixin, generics.RetrieveUpdateDestroyAPIView):
    serializer_class = UserReviewSerializer
    lookup_url_kwarg = "review_id"
    permission_classes = (IsAuthenticatedOrReadOnly,)
    parser_classes = (JSONParser, MultiPartParser, FormParser)

    def get_queryset(self):
        if self.request.method == "GET":
            return super().get_queryset()
        return review_response_queryset()

    @transaction.atomic
    def retrieve(self, request, *args, **kwargs):
        review = self.get_object()
        UserReview.objects.filter(pk=review.pk).update(view_count=F("view_count") + 1)
        review = review_response_queryset().get(pk=review.pk)
        return Response(UserReviewSerializer(review).data)

    def ensure_owner(self, review):
        if review.user_id != self.request.user.id:
            raise PermissionDenied("You do not have permission to modify this review.")

    @transaction.atomic
    def partial_update(self, request, *args, **kwargs):
        review = self.get_object()
        self.ensure_owner(review)
        affected_liked_users = list(review.likes.exclude(user_id=request.user.id).select_related("user"))
        serializer = UserReviewWriteSerializer(
            review,
            data=request.data,
            partial=True,
            context={"request": request},
        )
        serializer.is_valid(raise_exception=True)
        review = serializer.save()
        schedule_user_preference_pending(request.user)
        for liked_review in affected_liked_users:
            schedule_user_preference_pending(liked_review.user)
        review = review_response_queryset().get(pk=review.pk)
        return Response(UserReviewSerializer(review).data)

    @transaction.atomic
    def destroy(self, request, *args, **kwargs):
        review = self.get_object()
        self.ensure_owner(review)
        affected_liked_users = list(review.likes.exclude(user_id=request.user.id).select_related("user"))
        review.delete()
        schedule_user_preference_pending(request.user)
        for liked_review in affected_liked_users:
            schedule_user_preference_pending(liked_review.user)
        return Response(status=204)


class ReviewLikeAPIView(APIView):
    permission_classes = (IsAuthenticatedOrReadOnly,)

    def get_review(self):
        return get_object_or_404(
            UserReview.objects.filter(moderation_status=ReviewModerationStatus.VISIBLE),
            pk=self.kwargs["review_id"],
        )

    @transaction.atomic
    def post(self, request, *args, **kwargs):
        review = self.get_review()
        _, created = UserReviewLike.objects.get_or_create(user=request.user, review=review)
        if created:
            UserReview.objects.filter(pk=review.pk).update(like_count=F("like_count") + 1)
            schedule_user_preference_pending(request.user)
        review.refresh_from_db(fields=["like_count"])
        return Response(
            {
                "liked": True,
                "review_id": review.id,
                "like_count": review.like_count,
            }
        )

    @transaction.atomic
    def delete(self, request, *args, **kwargs):
        review = self.get_review()
        deleted_count, _ = UserReviewLike.objects.filter(user=request.user, review=review).delete()
        if deleted_count:
            UserReview.objects.filter(pk=review.pk, like_count__gt=0).update(like_count=F("like_count") - 1)
            schedule_user_preference_pending(request.user)
        review.refresh_from_db(fields=["like_count"])
        return Response(
            {
                "liked": False,
                "review_id": review.id,
                "like_count": review.like_count,
            }
        )
