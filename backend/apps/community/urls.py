from django.urls import path

from .views import (
    ReviewCommentDetailAPIView,
    ReviewCommentListAPIView,
    ReviewLikeAPIView,
    UserReviewDetailAPIView,
    UserReviewListAPIView,
)


app_name = "community"

urlpatterns = [
    path("", UserReviewListAPIView.as_view(), name="review-list"),
    path("<int:review_id>/like/", ReviewLikeAPIView.as_view(), name="review-like"),
    path("<int:review_id>/comments/", ReviewCommentListAPIView.as_view(), name="review-comment-list"),
    path(
        "<int:review_id>/comments/<int:comment_id>/",
        ReviewCommentDetailAPIView.as_view(),
        name="review-comment-detail",
    ),
    path("<int:review_id>/", UserReviewDetailAPIView.as_view(), name="review-detail"),
]
