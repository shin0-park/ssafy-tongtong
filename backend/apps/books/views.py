import json
from hashlib import sha256

from django.core.cache import cache
from rest_framework import generics, status
from rest_framework.response import Response
from rest_framework.views import APIView

from apps.common.pagination import StandardPageNumberPagination
from apps.integrations.data4library import (
    Data4LibraryAPIError,
    Data4LibraryClient,
    Data4LibraryConfigurationError,
)

from .models import Book, PopularBookSnapshot
from .serializers import (
    BookDetailSerializer,
    BookListSerializer,
    PopularBookItemSerializer,
    PopularBookSnapshotSerializer,
)
from .services import (
    serialize_book_holding_libraries,
    serialize_data4library_book,
    upsert_book_from_data4library,
)


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
DEFAULT_POPULAR_BOOK_LIMIT = 10
MAX_POPULAR_BOOK_LIMIT = 50
DATA4LIBRARY_CACHE_SECONDS = 60 * 60 * 6


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


class PopularBookListAPIView(APIView):
    def get(self, request):
        try:
            limit = parse_limited_positive_int(
                request.query_params.get("limit"),
                default=DEFAULT_POPULAR_BOOK_LIMIT,
                maximum=MAX_POPULAR_BOOK_LIMIT,
            )
        except ValueError:
            return Response({"detail": "limit must be a positive integer."}, status=status.HTTP_400_BAD_REQUEST)

        region = request.query_params.get("region", "21").strip() or "21"
        snapshot = (
            PopularBookSnapshot.objects.filter(region_code=region)
            .prefetch_related("items__book")
            .order_by("-period_end", "-fetched_at", "-id")
            .first()
        )
        if snapshot is None:
            return Response(
                {
                    "snapshot": None,
                    "items": [],
                }
            )

        items = list(snapshot.items.select_related("book").order_by("rank", "id")[:limit])
        return Response(
            {
                "snapshot": PopularBookSnapshotSerializer(snapshot).data,
                "items": PopularBookItemSerializer(items, many=True).data,
            }
        )


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
            payload = get_cached_data4library_payload(
                "book-search",
                search_params,
                lambda: Data4LibraryClient().search_books(search_params),
            )
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


class BookHoldingLibraryListAPIView(APIView):
    def get(self, request, isbn13):
        page = parse_positive_int(request.query_params.get("page"), default=1)
        page_size = min(parse_positive_int(request.query_params.get("page_size"), default=20), MAX_SEARCH_PAGE_SIZE)

        try:
            payload = get_cached_data4library_payload(
                "book-holdings",
                {
                    "isbn13": isbn13,
                    "page": page,
                    "page_size": page_size,
                    "region": "21",
                },
                lambda: Data4LibraryClient().get_book_libraries(
                    isbn13=isbn13,
                    page=page,
                    page_size=page_size,
                    region="21",
                ),
            )
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

        return Response(
            {
                "isbn13": isbn13,
                "source": "data4library",
                "count": payload["count"],
                "page": page,
                "page_size": page_size,
                "results": serialize_book_holding_libraries(payload["results"]),
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


def parse_limited_positive_int(value, *, default, maximum):
    if value in (None, ""):
        return default
    try:
        parsed = int(value)
    except (TypeError, ValueError) as exc:
        raise ValueError("Expected integer.") from exc
    if parsed <= 0:
        raise ValueError("Expected positive integer.")
    return min(parsed, maximum)


def get_cached_data4library_payload(scope, params, fetcher):
    cache_key = build_data4library_cache_key(scope, params)
    cached = cache.get(cache_key)
    if cached is not None:
        return cached
    payload = fetcher()
    cache.set(cache_key, payload, DATA4LIBRARY_CACHE_SECONDS)
    return payload


def build_data4library_cache_key(scope, params):
    encoded = json.dumps(params, ensure_ascii=False, sort_keys=True, default=str)
    digest = sha256(encoded.encode("utf-8")).hexdigest()
    return f"data4library:{scope}:{digest}"
