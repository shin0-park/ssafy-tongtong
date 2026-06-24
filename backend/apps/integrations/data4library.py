import json
import re
from dataclasses import dataclass
from datetime import date
from typing import Any
from urllib.error import HTTPError, URLError
from urllib.parse import urlencode
from urllib.request import urlopen

from django.conf import settings


class Data4LibraryConfigurationError(Exception):
    pass


class Data4LibraryAPIError(Exception):
    def __init__(
        self,
        message,
        *,
        endpoint=None,
        request_preview=None,
        status_code=None,
        reason=None,
        content_type=None,
        body_preview=None,
        original_exception_class=None,
        json_parse_failed=False,
    ):
        super().__init__(message)
        self.endpoint = endpoint
        self.request_preview = request_preview or {}
        self.status_code = status_code
        self.reason = reason
        self.content_type = content_type
        self.body_preview = body_preview
        self.original_exception_class = original_exception_class
        self.json_parse_failed = json_parse_failed


@dataclass
class Data4LibraryBook:
    isbn13: str
    title: str
    authors_text: str
    publisher: str
    publication_year: int | None
    addition_symbol: str
    volume: str
    kdc_class_no: str
    kdc_class_name: str
    cover_image_url: str
    source_detail_url: str
    loan_count: int | None


@dataclass
class Data4LibraryBookDetail:
    isbn13: str
    title: str
    authors_text: str
    publisher: str
    publication_date: date | None
    publication_year: int | None
    addition_symbol: str
    volume: str
    kdc_class_no: str
    kdc_class_name: str
    description: str
    cover_image_url: str
    source_detail_url: str


@dataclass
class Data4LibraryPopularBook:
    rank: int | None
    book: Data4LibraryBook
    source_payload: dict


@dataclass
class Data4LibraryBookLibrary:
    external_library_key: str
    name: str
    address: str
    homepage_url: str
    phone: str
    latitude: str
    longitude: str
    call_number: str
    loan_available: bool | None
    loan_status: str


@dataclass
class Data4LibraryLibrary:
    external_library_key: str
    name: str
    address: str
    homepage_url: str
    phone: str
    latitude: str
    longitude: str
    closed: str
    operating_time: str
    book_count: int | None


class Data4LibraryClient:
    provider_code = "data4library"

    def __init__(self, api_key=None, base_url=None, timeout=5):
        self.api_key = api_key if api_key is not None else settings.DATA4LIBRARY_API_KEY
        self.base_url = (base_url if base_url is not None else settings.DATA4LIBRARY_BASE_URL).rstrip("/")
        self.timeout = timeout

    def search_books(self, params):
        if not self.api_key:
            raise Data4LibraryConfigurationError("DATA4LIBRARY_API_KEY is not configured.")

        request_params = {
            "authKey": self.api_key,
            "format": "json",
            **params,
        }
        payload = self._get_json("srchBooks", request_params)
        response = payload.get("response", payload)
        docs = response.get("docs", {})
        raw_items = [unwrap_item(item, "doc") for item in ensure_list(docs.get("doc") if isinstance(docs, dict) else docs)]

        return {
            "num_found": parse_int(response.get("numFound"), default=0),
            "results": [normalize_book(item) for item in raw_items],
        }

    def get_book_libraries(self, isbn13, page=1, page_size=20, region="21"):
        if not self.api_key:
            raise Data4LibraryConfigurationError("DATA4LIBRARY_API_KEY is not configured.")

        request_params = {
            "authKey": self.api_key,
            "format": "json",
            "isbn": isbn13,
            "region": region,
            "pageNo": page,
            "pageSize": page_size,
        }
        payload = self._get_json("libSrchByBook", request_params)
        response = payload.get("response", payload)
        libs = response.get("libs", {})
        raw_items = [unwrap_item(item, "lib") for item in ensure_list(libs.get("lib") if isinstance(libs, dict) else libs)]
        results = [normalize_book_library(item) for item in raw_items]

        return {
            "count": parse_int(response.get("numFound"), default=len(results)),
            "results": results,
        }

    def get_popular_books(self, params):
        if not self.api_key:
            raise Data4LibraryConfigurationError("DATA4LIBRARY_API_KEY is not configured.")

        request_params = {
            "authKey": self.api_key,
            "format": "json",
            **params,
        }
        payload = self._get_json("loanItemSrch", request_params)
        return parse_popular_books_payload(payload)

    def get_book_detail(self, isbn13, loaninfo=False):
        if not self.api_key:
            raise Data4LibraryConfigurationError("DATA4LIBRARY_API_KEY is not configured.")

        request_params = {
            "authKey": self.api_key,
            "format": "json",
            "isbn13": isbn13,
            "loaninfoYN": "Y" if loaninfo else "N",
        }
        payload = self._get_json("srchDtlList", request_params)
        return parse_book_detail_payload(payload)

    def list_libraries(self, region="21", page=1, page_size=100):
        if not self.api_key:
            raise Data4LibraryConfigurationError("DATA4LIBRARY_API_KEY is not configured.")

        request_params = {
            "authKey": self.api_key,
            "format": "json",
            "region": region,
            "pageNo": page,
            "pageSize": page_size,
        }
        payload = self._get_json("libSrch", request_params)
        return parse_libraries_payload(payload)

    def _get_json(self, endpoint, params):
        url = f"{self.base_url}/{endpoint}?{urlencode(params)}"
        request_preview = build_request_preview(self.base_url, endpoint, params)
        try:
            with urlopen(url, timeout=self.timeout) as response:
                charset = response.headers.get_content_charset() or "utf-8"
                body = response.read().decode(charset)
                content_type = response.headers.get("content-type", "")
        except HTTPError as exc:
            body_preview = read_error_body_preview(exc)
            raise Data4LibraryAPIError(
                f"Data4Library request failed with status {exc.code}.",
                endpoint=endpoint,
                request_preview=request_preview,
                status_code=exc.code,
                reason=exc.reason,
                content_type=exc.headers.get("content-type", ""),
                body_preview=body_preview,
                original_exception_class=exc.__class__.__name__,
            ) from exc
        except URLError as exc:
            raise Data4LibraryAPIError(
                "Data4Library request failed.",
                endpoint=endpoint,
                request_preview=request_preview,
                reason=str(exc.reason),
                original_exception_class=exc.__class__.__name__,
            ) from exc
        except TimeoutError as exc:
            raise Data4LibraryAPIError(
                "Data4Library request timed out.",
                endpoint=endpoint,
                request_preview=request_preview,
                original_exception_class=exc.__class__.__name__,
            ) from exc

        try:
            return json.loads(body)
        except json.JSONDecodeError as exc:
            raise Data4LibraryAPIError(
                "Data4Library returned invalid JSON.",
                endpoint=endpoint,
                request_preview=request_preview,
                content_type=content_type,
                body_preview=mask_sensitive_text(body[:300]),
                original_exception_class=exc.__class__.__name__,
                json_parse_failed=True,
            ) from exc


def parse_libraries_payload(payload):
    response = payload.get("response", payload)
    libs = response.get("libs", {})
    raw_items = [unwrap_item(item, "lib") for item in ensure_list(libs.get("lib") if isinstance(libs, dict) else libs)]
    results = [normalize_library(item) for item in raw_items]

    return {
        "count": parse_int(response.get("numFound"), default=len(results)),
        "result_num": parse_int(response.get("resultNum"), default=len(results)),
        "results": results,
    }


def parse_popular_books_payload(payload):
    response = payload.get("response", payload)
    docs = response.get("docs", {})
    raw_items = [unwrap_item(item, "doc") for item in ensure_list(docs.get("doc") if isinstance(docs, dict) else docs)]
    results = [normalize_popular_book(item) for item in raw_items]

    return {
        "num_found": parse_int(response.get("numFound"), default=len(results)),
        "result_num": parse_int(response.get("resultNum"), default=len(results)),
        "results": results,
    }


def parse_book_detail_payload(payload):
    response = payload.get("response", payload)
    detail = response.get("detail", {})
    raw_items = ensure_list(detail.get("book") if isinstance(detail, dict) else detail)
    if not raw_items:
        docs = response.get("docs", {})
        raw_items = [unwrap_item(item, "doc") for item in ensure_list(docs.get("doc") if isinstance(docs, dict) else docs)]
    if not raw_items and isinstance(response.get("book"), dict):
        raw_items = [response["book"]]
    if not raw_items:
        return None
    return normalize_book_detail(unwrap_item(raw_items[0], "book"))


def ensure_list(value: Any):
    if value is None or value == "":
        return []
    if isinstance(value, list):
        return value
    return [value]


def unwrap_item(value, key):
    if isinstance(value, dict) and key in value and len(value) == 1:
        return value[key]
    return value


def parse_int(value, default=None):
    if value in (None, ""):
        return default
    try:
        return int(value)
    except (TypeError, ValueError):
        return default


def parse_bool(value):
    if value in (None, ""):
        return None
    normalized = str(value).strip().lower()
    if normalized in {"y", "yes", "true", "1", "available", "loan_available"}:
        return True
    if normalized in {"n", "no", "false", "0", "unavailable", "loan_unavailable"}:
        return False
    return None


def parse_date(value):
    raw = str(value or "").strip()
    if not raw:
        return None
    digits = re.sub(r"\D", "", raw)
    if len(digits) >= 8:
        try:
            return date(int(digits[:4]), int(digits[4:6]), int(digits[6:8]))
        except ValueError:
            return None
    if len(digits) == 4:
        try:
            return date(int(digits), 1, 1)
        except ValueError:
            return None
    return None


def parse_publication_year_from_date(value):
    parsed = parse_date(value)
    if parsed:
        return parsed.year
    return parse_int(value)


def first_value(item, *keys):
    for key in keys:
        value = item.get(key)
        if value not in (None, ""):
            return value
    return ""


def build_request_preview(base_url, endpoint, params):
    masked_params = {
        key: "<masked>" if key.lower() in {"authkey", "authorization", "token", "apikey", "api_key"} else value
        for key, value in params.items()
    }
    path = f"{base_url.rstrip('/')}/{endpoint}".replace("http://data4library.kr", "")
    return {
        "endpoint": endpoint,
        "path": path,
        "params": masked_params,
    }


def read_error_body_preview(exc):
    try:
        charset = exc.headers.get_content_charset() or "utf-8"
        body = exc.read().decode(charset, errors="replace")
    except Exception:
        return ""
    return mask_sensitive_text(body[:300])


def mask_sensitive_text(value):
    return re.sub(
        r"(?i)\b(authKey|serviceKey|apiKey|api_key|token|authorization)=([^&\s]+)",
        r"\1=<masked>",
        str(value or ""),
    )


def normalize_book(item):
    return Data4LibraryBook(
        isbn13=str(item.get("isbn13") or "").strip(),
        title=str(item.get("bookname") or "").strip(),
        authors_text=str(item.get("authors") or "").strip(),
        publisher=str(item.get("publisher") or "").strip(),
        publication_year=parse_int(item.get("publication_year")),
        addition_symbol=str(item.get("addition_symbol") or "").strip(),
        volume=str(item.get("vol") or "").strip(),
        kdc_class_no=str(item.get("class_no") or "").strip(),
        kdc_class_name=str(item.get("class_nm") or "").strip(),
        cover_image_url=str(item.get("bookImageURL") or "").strip(),
        source_detail_url=str(item.get("bookDtlUrl") or "").strip(),
        loan_count=parse_int(item.get("loan_count")),
    )


def normalize_popular_book(item):
    book = normalize_book(item)
    rank = parse_int(first_value(item, "ranking", "rank", "no"))
    loan_count = parse_int(first_value(item, "loan_count", "loanCnt", "loan_count_sum"))
    if loan_count is not None:
        book.loan_count = loan_count
    return Data4LibraryPopularBook(
        rank=rank,
        book=book,
        source_payload={key: value for key, value in item.items() if key != "authKey"},
    )


def normalize_book_detail(item):
    publication_date = parse_date(first_value(item, "publication_date", "publicationDate", "pubDate"))
    return Data4LibraryBookDetail(
        isbn13=str(first_value(item, "isbn13", "isbn")).strip(),
        title=str(first_value(item, "bookname", "bookName", "title")).strip(),
        authors_text=str(first_value(item, "authors", "author")).strip(),
        publisher=str(first_value(item, "publisher")).strip(),
        publication_date=publication_date,
        publication_year=publication_date.year if publication_date else parse_publication_year_from_date(
            first_value(item, "publication_year", "publicationDate", "pubDate")
        ),
        addition_symbol=str(first_value(item, "addition_symbol", "additionSymbol")).strip(),
        volume=str(first_value(item, "vol", "volume")).strip(),
        kdc_class_no=str(first_value(item, "class_no", "classNo", "kdc_class_no")).strip(),
        kdc_class_name=str(first_value(item, "class_nm", "className", "kdc_class_name")).strip(),
        description=str(first_value(item, "description", "bookDescription", "contents")).strip(),
        cover_image_url=str(first_value(item, "bookImageURL", "bookImageUrl", "cover_image_url")).strip(),
        source_detail_url=str(first_value(item, "bookDtlUrl", "bookDetailUrl", "source_detail_url")).strip(),
    )


def normalize_book_library(item):
    return Data4LibraryBookLibrary(
        external_library_key=str(first_value(item, "libCode", "libcode", "lib_code")).strip(),
        name=str(first_value(item, "libName", "libname", "lib_name")).strip(),
        address=str(first_value(item, "address", "addr")).strip(),
        homepage_url=str(first_value(item, "homepage", "homepageURL", "homepage_url")).strip(),
        phone=str(first_value(item, "tel", "phone")).strip(),
        latitude=str(first_value(item, "latitude", "lat")).strip(),
        longitude=str(first_value(item, "longitude", "lng", "lon")).strip(),
        call_number=str(first_value(item, "callNumber", "call_no", "callNo")).strip(),
        loan_available=parse_bool(first_value(item, "loanAvailable", "loan_available", "loanYn")),
        loan_status=str(first_value(item, "loanStatus", "loan_status", "hasBook")).strip(),
    )


def normalize_library(item):
    return Data4LibraryLibrary(
        external_library_key=str(first_value(item, "libCode", "libcode", "lib_code")).strip(),
        name=str(first_value(item, "libName", "libname", "lib_name")).strip(),
        address=str(first_value(item, "address", "addr")).strip(),
        homepage_url=str(first_value(item, "homepage", "homepageURL", "homepage_url")).strip(),
        phone=str(first_value(item, "tel", "phone")).strip(),
        latitude=str(first_value(item, "latitude", "lat")).strip(),
        longitude=str(first_value(item, "longitude", "lng", "lon")).strip(),
        closed=str(first_value(item, "closed", "close")).strip(),
        operating_time=str(first_value(item, "operatingTime", "operating_time")).strip(),
        book_count=parse_int(first_value(item, "BookCount", "bookCount", "book_count")),
    )
