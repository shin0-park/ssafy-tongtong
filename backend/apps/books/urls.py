from django.urls import path

from .views import BookDetailAPIView, BookListAPIView, BookSearchAPIView


app_name = "books"

urlpatterns = [
    path("", BookListAPIView.as_view(), name="book-list"),
    path("search/", BookSearchAPIView.as_view(), name="book-search"),
    path("<str:isbn13>/", BookDetailAPIView.as_view(), name="book-detail"),
]
