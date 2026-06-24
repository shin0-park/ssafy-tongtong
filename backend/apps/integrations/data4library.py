import json
from dataclasses import dataclass
from typing import Any
from urllib.error import HTTPError, URLError
from urllib.parse import urlencode
from urllib.request import urlopen

from django.conf import settings


class Data4LibraryConfigurationError(Exception):
    pass


class Data4LibraryAPIError(Exception):
    pass


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

    def _get_json(self, endpoint, params):
        url = f"{self.base_url}/{endpoint}?{urlencode(params)}"
        try:
            with urlopen(url, timeout=self.timeout) as response:
                charset = response.headers.get_content_charset() or "utf-8"
                body = response.read().decode(charset)
        except HTTPError as exc:
            raise Data4LibraryAPIError(f"Data4Library request failed with status {exc.code}.") from exc
        except URLError as exc:
            raise Data4LibraryAPIError("Data4Library request failed.") from exc
        except TimeoutError as exc:
            raise Data4LibraryAPIError("Data4Library request timed out.") from exc

        try:
            return json.loads(body)
        except json.JSONDecodeError as exc:
            raise Data4LibraryAPIError("Data4Library returned invalid JSON.") from exc


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
