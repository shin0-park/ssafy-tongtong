from rest_framework import generics, status
from rest_framework.response import Response
from rest_framework.views import APIView

from apps.common.pagination import StandardPageNumberPagination
from apps.integrations.data4library import (
    Data4LibraryAPIError,
    Data4LibraryClient,
    Data4LibraryConfigurationError,
)

from .models import Book
from .serializers import BookDetailSerializer, BookListSerializer
from .services import serialize_data4library_book, upsert_book_from_data4library


SEARCH_TYPE_PARAM_MAP = {
    "title": "title",
    "author": "author",
    "isbn": "isbn13",
    "keyword": "keyword",
    "publisher": "publisher",
}
DIRECT_SEARCH_PARAMS = ("title", "author", "isbn13", "keyword", "publisher")
ALLOWED_SORT_VALUES = {"loan", "title", "author", "pub", "pubYear", "isbn"}
ALLOWED_ORDER_VALUES = {"asc", "desc"}
MAX_SEARCH_PAGE_SIZE = 100


class BookQueryMixin:
    serializer_class = BookListSerializer

    def get_queryset(self):
        return (
            Book.objects.filter(is_active=True)
            .prefetch_related("tag_links__tag")
            .order_by("title", "id")
        )


class BookListAPIView(BookQueryMixin, generics.ListAPIView):
    serializer_class = BookListSerializer
    pagination_class = StandardPageNumberPagination


class BookDetailAPIView(BookQueryMixin, generics.RetrieveAPIView):
    serializer_class = BookDetailSerializer
    lookup_field = "isbn13"
    lookup_url_kwarg = "isbn13"


class BookSearchAPIView(APIView):
    def get(self, request):
        try:
            search_params = build_search_params(request.query_params)
        except ValueError as exc:
            return Response({"detail": str(exc)}, status=status.HTTP_400_BAD_REQUEST)

        page = parse_positive_int(request.query_params.get("page"), default=1)
        page_size = min(parse_positive_int(request.query_params.get("page_size"), default=20), MAX_SEARCH_PAGE_SIZE)
        search_params["pageNo"] = page
        search_params["pageSize"] = page_size

        sort = request.query_params.get("sort", "").strip()
        if sort:
            if sort not in ALLOWED_SORT_VALUES:
                return Response({"detail": "Invalid sort value."}, status=status.HTTP_400_BAD_REQUEST)
            search_params["sort"] = sort

        order = request.query_params.get("order", "").strip()
        if order:
            if order not in ALLOWED_ORDER_VALUES:
                return Response({"detail": "Invalid order value."}, status=status.HTTP_400_BAD_REQUEST)
            search_params["order"] = order

        try:
            payload = Data4LibraryClient().search_books(search_params)
        except Data4LibraryConfigurationError:
            return Response(
                {"detail": "Data4Library API key is not configured."},
                status=status.HTTP_503_SERVICE_UNAVAILABLE,
            )
        except Data4LibraryAPIError:
            return Response(
                {"detail": "Data4Library API request failed."},
                status=status.HTTP_502_BAD_GATEWAY,
            )

        results = []
        for book_data in payload["results"]:
            local_book = upsert_book_from_data4library(book_data)
            results.append(serialize_data4library_book(book_data, local_book))

        return Response(
            {
                "source": "data4library",
                "num_found": payload["num_found"],
                "page": page,
                "page_size": page_size,
                "results": results,
            }
        )


def build_search_params(query_params):
    search_params = {}
    search_type = query_params.get("search_type", "").strip()
    query = query_params.get("q", "").strip()
    if search_type or query:
        if search_type not in SEARCH_TYPE_PARAM_MAP or not query:
            raise ValueError("search_type and q must be provided together.")
        search_params[SEARCH_TYPE_PARAM_MAP[search_type]] = query

    for param in DIRECT_SEARCH_PARAMS:
        value = query_params.get(param, "").strip()
        if value:
            search_params[param] = value

    if not search_params:
        raise ValueError("At least one search condition is required.")

    return search_params


def parse_positive_int(value, default):
    try:
        parsed = int(value)
    except (TypeError, ValueError):
        return default
    return parsed if parsed > 0 else default
