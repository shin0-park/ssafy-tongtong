from django.urls import path

from apps.myoutings.views import (
    LikedReviewListAPIView,
    MyReviewListAPIView,
    SavedBookListAPIView,
    SavedLibraryListAPIView,
    SavedProgramListAPIView,
)


app_name = "myoutings"

urlpatterns = [
    path("libraries/", SavedLibraryListAPIView.as_view(), name="saved-library-list"),
    path("books/", SavedBookListAPIView.as_view(), name="saved-book-list"),
    path("programs/", SavedProgramListAPIView.as_view(), name="saved-program-list"),
    path("reviews/", MyReviewListAPIView.as_view(), name="my-review-list"),
    path("liked-reviews/", LikedReviewListAPIView.as_view(), name="liked-review-list"),
]
