from django.urls import path

from apps.myoutings.views import LibrarySaveAPIView

from .views import LibraryDetailAPIView, LibraryListAPIView, LibrarySimilarAPIView


app_name = "libraries"

urlpatterns = [
    path("", LibraryListAPIView.as_view(), name="library-list"),
    path("<int:library_id>/save/", LibrarySaveAPIView.as_view(), name="library-save"),
    path("<int:library_id>/similar/", LibrarySimilarAPIView.as_view(), name="library-similar"),
    path("<int:library_id>/", LibraryDetailAPIView.as_view(), name="library-detail"),
]
