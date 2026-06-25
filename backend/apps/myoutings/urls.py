from django.urls import path

from apps.myoutings.views import (
    LikedReviewListAPIView,
    MyCommentListAPIView,
    MyOutingsDashboardAPIView,
    MyReviewListAPIView,
    SavedBookListAPIView,
    SavedLibraryListAPIView,
    SavedProgramListAPIView,
)


app_name = "myoutings"

urlpatterns = [
    path("dashboard/", MyOutingsDashboardAPIView.as_view(), name="dashboard"),
    path("libraries/", SavedLibraryListAPIView.as_view(), name="saved-library-list"),
    path("books/", SavedBookListAPIView.as_view(), name="saved-book-list"),
    path("programs/", SavedProgramListAPIView.as_view(), name="saved-program-list"),
    path("reviews/", MyReviewListAPIView.as_view(), name="my-review-list"),
    path("comments/", MyCommentListAPIView.as_view(), name="my-comment-list"),
    path("liked-reviews/", LikedReviewListAPIView.as_view(), name="liked-review-list"),
]
