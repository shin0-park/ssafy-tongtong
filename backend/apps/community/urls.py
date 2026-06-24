from django.urls import path

from .views import UserReviewDetailAPIView, UserReviewListAPIView


app_name = "community"

urlpatterns = [
    path("", UserReviewListAPIView.as_view(), name="review-list"),
    path("<int:review_id>/", UserReviewDetailAPIView.as_view(), name="review-detail"),
]
