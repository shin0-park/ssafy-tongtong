from django.urls import path

from apps.myoutings.views import BookSaveAPIView

from .views import BookDetailAPIView, BookHoldingLibraryListAPIView, BookListAPIView, BookSearchAPIView


app_name = "books"

urlpatterns = [
    path("", BookListAPIView.as_view(), name="book-list"),
    path("search/", BookSearchAPIView.as_view(), name="book-search"),
    path("<str:isbn13>/save/", BookSaveAPIView.as_view(), name="book-save"),
    path("<str:isbn13>/libraries/", BookHoldingLibraryListAPIView.as_view(), name="book-holding-libraries"),
    path("<str:isbn13>/", BookDetailAPIView.as_view(), name="book-detail"),
]
