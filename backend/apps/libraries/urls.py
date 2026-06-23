from django.urls import path

from .views import LibraryDetailAPIView, LibraryListAPIView


app_name = "libraries"

urlpatterns = [
    path("", LibraryListAPIView.as_view(), name="library-list"),
    path("<int:library_id>/", LibraryDetailAPIView.as_view(), name="library-detail"),
]
