from django.urls import path

from apps.myoutings.views import (
    SavedBookListAPIView,
    SavedLibraryListAPIView,
    SavedProgramListAPIView,
)


app_name = "myoutings"

urlpatterns = [
    path("libraries/", SavedLibraryListAPIView.as_view(), name="saved-library-list"),
    path("books/", SavedBookListAPIView.as_view(), name="saved-book-list"),
    path("programs/", SavedProgramListAPIView.as_view(), name="saved-program-list"),
]
