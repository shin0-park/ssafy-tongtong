import json
import re
import xml.etree.ElementTree as ET
from dataclasses import dataclass
from datetime import date
from math import ceil
from typing import Any
from urllib.error import HTTPError, URLError
from urllib.parse import urlencode
from urllib.request import urlopen

from django.conf import settings


class PublicHolidayConfigurationError(Exception):
    pass


class PublicHolidayAPIError(Exception):
    def __init__(
        self,
        message,
        *,
        request_preview=None,
        status_code=None,
        reason=None,
        content_type=None,
        body_preview=None,
        original_exception_class=None,
    ):
        super().__init__(message)
        self.request_preview = request_preview or {}
        self.status_code = status_code
        self.reason = reason
        self.content_type = content_type
        self.body_preview = body_preview
        self.original_exception_class = original_exception_class


@dataclass(frozen=True)
class PublicHolidayItem:
    date: date
    source_seq: str
    date_kind: str
    name: str
    holiday_code: str
    is_public_holiday: bool


class PublicHolidayClient:
    provider_code = "data_go_kr"

    def __init__(self, api_key=None, base_url=None, operation=None, num_of_rows=None, timeout=10):
        self.api_key = api_key if api_key is not None else settings.DATA_GO_KR_API_KEY
        self.base_url = (base_url if base_url is not None else settings.PUBLIC_HOLIDAY_API_BASE_URL).rstrip("/")
        self.operation = operation if operation is not None else settings.PUBLIC_HOLIDAY_API_OPERATION
        self.num_of_rows = int(num_of_rows if num_of_rows is not None else settings.PUBLIC_HOLIDAY_API_NUM_OF_ROWS)
        self.timeout = timeout

    def fetch_month(self, year, month):
        if not self.api_key:
            raise PublicHolidayConfigurationError("DATA_GO_KR_API_KEY is not configured.")
        if not 1 <= int(month) <= 12:
            raise PublicHolidayAPIError("month must be between 1 and 12.")

        first_page = self._fetch_page(year, month, page=1)
        holidays = first_page["items"]
        total_count = first_page["total_count"]
        if total_count <= len(holidays):
            return holidays

        total_pages = ceil(total_count / self.num_of_rows)
        for page in range(2, total_pages + 1):
            holidays.extend(self._fetch_page(year, month, page=page)["items"])
        return holidays

    def _fetch_page(self, year, month, page):
        params = {
            "ServiceKey": self.api_key,
            "solYear": str(year),
            "solMonth": f"{int(month):02d}",
            "pageNo": str(page),
            "numOfRows": str(self.num_of_rows),
            "_type": "json",
        }
        url = f"{self.base_url}/{self.operation}?{urlencode(params, safe='%')}"
        request_preview = build_request_preview(self.base_url, self.operation, params)
        try:
            with urlopen(url, timeout=self.timeout) as response:
                charset = response.headers.get_content_charset() or "utf-8"
                body = response.read().decode(charset, errors="replace")
                content_type = response.headers.get("content-type", "")
        except HTTPError as exc:
            raise PublicHolidayAPIError(
                f"Public holiday request failed with status {exc.code}.",
                request_preview=request_preview,
                status_code=exc.code,
                reason=exc.reason,
                content_type=exc.headers.get("content-type", ""),
                body_preview=read_error_body_preview(exc),
                original_exception_class=exc.__class__.__name__,
            ) from exc
        except URLError as exc:
            raise PublicHolidayAPIError(
                "Public holiday request failed.",
                request_preview=request_preview,
                reason=str(exc.reason),
                original_exception_class=exc.__class__.__name__,
            ) from exc
        except TimeoutError as exc:
            raise PublicHolidayAPIError(
                "Public holiday request timed out.",
                request_preview=request_preview,
                original_exception_class=exc.__class__.__name__,
            ) from exc

        return parse_public_holiday_payload(
            body,
            content_type=content_type,
            request_preview=request_preview,
        )


def parse_public_holiday_payload(body, *, content_type="", request_preview=None):
    payload = parse_json_or_xml(body, content_type=content_type)
    response = payload.get("response", payload)
    if not isinstance(response, dict) or "body" not in response:
        raise PublicHolidayAPIError(
            "Public holiday API returned an unexpected response schema.",
            request_preview=request_preview,
            content_type=content_type,
            body_preview=mask_sensitive_text(str(payload)[:300]),
        )
    header = response.get("header", {})
    result_code = str(header.get("resultCode", "")).strip()
    result_msg = str(header.get("resultMsg", "")).strip()
    if result_code and result_code != "00":
        raise PublicHolidayAPIError(
            f"Public holiday API returned resultCode={result_code}.",
            request_preview=request_preview,
            reason=result_msg,
            body_preview=mask_sensitive_text(str(payload)[:300]),
        )

    body_payload = response.get("body", {})
    raw_items = get_nested(body_payload, "items", "item")
    items = [normalize_public_holiday_item(item) for item in ensure_list(raw_items)]
    return {
        "total_count": parse_int(body_payload.get("totalCount"), default=len(items)),
        "items": [item for item in items if item and item.is_public_holiday],
    }


def parse_json_or_xml(body, *, content_type=""):
    stripped = str(body or "").strip()
    if not stripped:
        raise PublicHolidayAPIError("Public holiday API returned an empty response.")

    if "json" in content_type.lower() or stripped.startswith(("{", "[")):
        try:
            return json.loads(stripped)
        except json.JSONDecodeError:
            pass

    try:
        root = ET.fromstring(stripped)
    except ET.ParseError as exc:
        raise PublicHolidayAPIError(
            "Public holiday API returned an unsupported response format.",
            content_type=content_type,
            body_preview=mask_sensitive_text(stripped[:300]),
            original_exception_class=exc.__class__.__name__,
        ) from exc
    return xml_element_to_dict(root)


def xml_element_to_dict(element):
    children = list(element)
    if not children:
        return (element.text or "").strip()

    result = {}
    for child in children:
        value = xml_element_to_dict(child)
        if child.tag in result:
            if not isinstance(result[child.tag], list):
                result[child.tag] = [result[child.tag]]
            result[child.tag].append(value)
        else:
            result[child.tag] = value
    return {element.tag: result} if element.tag == "response" else result


def normalize_public_holiday_item(item):
    if not isinstance(item, dict):
        return None

    holiday_date = parse_yyyymmdd(item.get("locdate"))
    source_seq = str(item.get("seq") or "").strip()
    date_kind = str(item.get("dateKind") or "").strip()
    name = str(item.get("dateName") or "").strip()
    is_public_holiday = str(item.get("isHoliday") or "").strip().upper() == "Y"
    if not holiday_date or not source_seq or not date_kind or not name:
        return None

    return PublicHolidayItem(
        date=holiday_date,
        source_seq=source_seq,
        date_kind=date_kind,
        name=name,
        holiday_code="",
        is_public_holiday=is_public_holiday,
    )


def ensure_list(value: Any):
    if value in (None, ""):
        return []
    if isinstance(value, list):
        return value
    return [value]


def get_nested(value, *keys):
    current = value
    for key in keys:
        if not isinstance(current, dict):
            return None
        current = current.get(key)
    return current


def parse_int(value, default=None):
    if value in (None, ""):
        return default
    try:
        return int(value)
    except (TypeError, ValueError):
        return default


def parse_yyyymmdd(value):
    raw = str(value or "").strip()
    if not raw:
        return None
    digits = re.sub(r"\D", "", raw)
    if len(digits) != 8:
        return None
    try:
        return date(int(digits[:4]), int(digits[4:6]), int(digits[6:8]))
    except ValueError:
        return None


def build_request_preview(base_url, operation, params):
    masked_params = {
        key: "<masked>" if key.lower() in {"servicekey", "authorization", "token", "apikey", "api_key"} else value
        for key, value in params.items()
    }
    path = f"{base_url.rstrip('/')}/{operation}".replace("http://apis.data.go.kr", "")
    return {
        "operation": operation,
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
        r"(?i)\b(ServiceKey|authKey|apiKey|api_key|token|authorization)=([^&\s]+)",
        r"\1=<masked>",
        str(value or ""),
    )
