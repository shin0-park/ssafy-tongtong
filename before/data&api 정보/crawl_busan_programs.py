"""
crawl_busan_programs.py

부산도서관포털 3개 게시판에서 '게시일 기준 특정 기간'의 문화프로그램 게시물을 수집하고,
GMS(OpenAI 호환 Chat Completions)로 Program 모델용 Django fixture JSON을 생성합니다.

설치:
    pip install requests beautifulsoup4 python-dotenv

.env 예시:
    GMS_API_KEY=발급받은_GMS_KEY
    GMS_OPENAI_BASE_URL=https://gms.ssafy.io/gmsapi/api.openai.com/v1
    GMS_MODEL=gpt-5-nano

실행 예시:
    python scripts/crawl_busan_programs.py \
      --library-fixture libraries/fixtures/libraries.json \
      --output programs/fixtures/programs_2026_06_by_post_date.json \
      --post-start-date 2026-06-01 \
      --post-end-date 2026-06-30 \
      --max-pages 50

주의:
- 기본 수집 기준은 '게시일'입니다.
- 첨부 PDF/이미지에만 핵심 정보가 있을 가능성이 큰 게시물은 기본적으로 제외합니다.
- Django fixture에서 ForeignKey 필드명은 보통 "library"입니다.
  Program 모델 필드가 실제로 library_id라면 --fixture-library-field library_id 로 바꾸세요.
"""

from __future__ import annotations

import argparse
import datetime as dt
import hashlib
import json
import os
import re
import sys
import time
from dataclasses import dataclass
from html import unescape
from typing import Any, Optional
from urllib.parse import parse_qs, urlencode, urljoin, urlparse, urlunparse

import requests
from bs4 import BeautifulSoup
from dotenv import load_dotenv


BASE_URL = "https://library.busan.go.kr"

DEFAULT_BOARDS = [
    {
        "name": "강좌신청",
        "source_board": "강좌신청",
        "url": "https://library.busan.go.kr/portal/board/index.do?menu_idx=67&manage_idx=595&board_idx=0&group_idx=0&rowCount=10&viewPage=1&search_type=title%2Bcontent",
        "manage_idx": "595",
        "menu_idx": "67",
    },
    {
        "name": "독서문화행사",
        "source_board": "독서문화행사",
        "url": "https://library.busan.go.kr/portal/board/index.do?menu_idx=17&manage_idx=596&rowCount=10&viewPage=1&search_type=title%2Bcontent",
        "manage_idx": "596",
        "menu_idx": "17",
    },
    {
        "name": "영화상영",
        "source_board": "영화상영",
        "url": "https://library.busan.go.kr/portal/board/index.do?menu_idx=18&manage_idx=597&rowCount=10&viewPage=1&search_type=title%2Bcontent",
        "manage_idx": "597",
        "menu_idx": "18",
    },
]

CATEGORY_CODES = {
    "lecture_humanities",
    "reading_writing",
    "culture_art",
    "experience_education",
    "exhibition",
    "other",
}

TARGET_CODES = {
    "infant",
    "elementary",
    "teen",
    "adult",
    "senior",
    "family",
    "all",
}

ATTACHMENT_EXTENSIONS = {
    ".pdf",
    ".jpg",
    ".jpeg",
    ".png",
    ".gif",
    ".bmp",
    ".webp",
    ".hwp",
    ".hwpx",
    ".doc",
    ".docx",
    ".ppt",
    ".pptx",
    ".xls",
    ".xlsx",
}

DATE_RE = re.compile(r"(20\d{2})[.\-/년\s]+(\d{1,2})[.\-/월\s]+(\d{1,2})")


@dataclass
class ListItem:
    board_name: str
    source_board: str
    list_url: str
    detail_url: str
    board_idx: Optional[str]
    source_library_label: Optional[str]
    title: str
    post_date: Optional[str]


@dataclass
class DetailPayload:
    item: ListItem
    body_text: str
    attachment_urls: list[str]
    skipped_reason: Optional[str] = None


def now_kst() -> dt.datetime:
    return dt.datetime.now(dt.timezone(dt.timedelta(hours=9)))


def today_kst() -> dt.date:
    return now_kst().date()


def iso_now_kst() -> str:
    return now_kst().replace(microsecond=0).isoformat()


def normalize_space(text: str) -> str:
    text = unescape(text or "")
    text = re.sub(r"\s+", " ", text)
    return text.strip()


def normalize_name(text: str) -> str:
    text = normalize_space(text)
    text = re.sub(r"\(.*?\)", "", text)
    text = text.replace("부산광역시립", "")
    text = text.replace("부산시립", "")
    text = text.replace("부산광역시", "")
    text = text.replace("도서관", "")
    text = re.sub(r"[\s·ㆍ\-_()]", "", text)
    return text.strip()


def sha256_text(text: str, length: Optional[int] = None) -> str:
    digest = hashlib.sha256((text or "").encode("utf-8")).hexdigest()
    return digest[:length] if length else digest


def parse_date(text: str) -> Optional[str]:
    if not text:
        return None

    m = DATE_RE.search(text)
    if not m:
        return None

    y, mo, d = map(int, m.groups())

    try:
        return dt.date(y, mo, d).isoformat()
    except ValueError:
        return None


def parse_iso_date(value: Any) -> Optional[dt.date]:
    if not value:
        return None

    if isinstance(value, dt.date):
        return value

    if not isinstance(value, str):
        return None

    value = value.strip()
    if not value:
        return None

    try:
        return dt.date.fromisoformat(value[:10])
    except ValueError:
        return None


def date_in_range(value: Optional[str], start: dt.date, end: dt.date) -> bool:
    parsed = parse_iso_date(value)
    if not parsed:
        return False
    return start <= parsed <= end


def calculate_application_status(
    required: Optional[bool],
    start_date: Optional[str],
    end_date: Optional[str],
    today: Optional[dt.date] = None,
) -> Optional[str]:
    today = today or today_kst()

    if required is False:
        return "신청없음"

    if required is not True:
        return None

    start = parse_iso_date(start_date)
    end = parse_iso_date(end_date)

    if not start or not end or start > end:
        return None

    if today < start:
        return None
    if start <= today <= end:
        return "신청가능"
    if today > end:
        return "신청마감"

    return None


def calculate_operation_status(
    start_date: Optional[str],
    end_date: Optional[str],
    today: Optional[dt.date] = None,
) -> Optional[str]:
    today = today or today_kst()

    start = parse_iso_date(start_date)
    end = parse_iso_date(end_date)

    if not start or not end or start > end:
        return None

    if today < start:
        return "예정"
    if start <= today <= end:
        return "진행중"
    if today > end:
        return "종료"

    return None


def set_query_param(url: str, **params: Any) -> str:
    parsed = urlparse(url)
    query = parse_qs(parsed.query)

    for key, value in params.items():
        if value is None:
            query.pop(key, None)
        else:
            query[key] = [str(value)]

    return urlunparse(parsed._replace(query=urlencode(query, doseq=True)))


def get_session() -> requests.Session:
    session = requests.Session()
    session.headers.update(
        {
            "User-Agent": (
                "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                "AppleWebKit/537.36 (KHTML, like Gecko) "
                "Chrome/124.0 Safari/537.36"
            ),
            "Accept-Language": "ko-KR,ko;q=0.9,en-US;q=0.8,en;q=0.7",
        }
    )
    return session


def fetch_html(session: requests.Session, url: str, timeout: int = 20) -> str:
    response = session.get(url, timeout=timeout)
    response.raise_for_status()
    response.encoding = response.apparent_encoding or "utf-8"
    return response.text


def extract_board_idx_from_url_or_text(text: str) -> Optional[str]:
    if not text:
        return None

    patterns = [
        r"board_idx[=:]\s*['\"]?(\d+)",
        r"boardIdx[=:]\s*['\"]?(\d+)",
        r"board_idx=(\d+)",
        r"boardIdx=(\d+)",
    ]

    for pattern in patterns:
        m = re.search(pattern, text)
        if m:
            return m.group(1)

    return None


def likely_detail_href(href: str) -> bool:
    if not href:
        return False

    href = unescape(href)

    return (
        "board" in href
        and (
            "view" in href
            or "detail" in href
            or "board_idx=" in href
            or "boardIdx=" in href
        )
    )


def make_detail_url_from_board_idx(board: dict[str, str], board_idx: str) -> str:
    return set_query_param(
        board["url"],
        menu_idx=board.get("menu_idx"),
        manage_idx=board.get("manage_idx"),
        board_idx=board_idx,
    )


def extract_url_from_onclick(onclick: str) -> Optional[str]:
    if not onclick:
        return None

    onclick = unescape(onclick)

    m = re.search(r"(?:location\.href|document\.location)\s*=\s*['\"]([^'\"]+)['\"]", onclick)
    if m:
        return m.group(1)

    m = re.search(r"['\"]([^'\"]*(?:view|detail|index)\.do[^'\"]*)['\"]", onclick)
    if m:
        return m.group(1)

    return None


def parse_row_title_and_library(row_text: str, post_date: str) -> tuple[str, Optional[str]]:
    text = row_text
    text = re.sub(r"^\s*\d+\s+", "", text)
    text = text.replace(post_date.replace("-", "."), "")
    text = text.replace(post_date, "")
    text = normalize_space(text)

    if not text:
        return "", None

    parts = text.split(" ", 1)

    if len(parts) == 1:
        return parts[0], None

    library_label, title = parts[0], parts[1]

    if len(title) < 2:
        return text, None

    return title.strip(), library_label.strip()


def extract_list_items_from_page(
    board: dict[str, str],
    html: str,
    page_url: str,
) -> list[ListItem]:
    soup = BeautifulSoup(html, "html.parser")
    items: list[ListItem] = []

    rows = soup.select("table tr")
    if not rows:
        rows = soup.select("li, .board-list li, .bbs-list li")

    for row in rows:
        row_text = normalize_space(row.get_text(" ", strip=True))

        if not row_text:
            continue

        if any(x in row_text for x in ["번호 도서관 제목", "검색조건", "총 게시물", "담당부서"]):
            continue

        if not re.match(r"^\s*\d+\s+", row_text):
            continue

        post_date = parse_date(row_text)
        if not post_date:
            continue

        detail_url = None
        board_idx = None

        for a in row.find_all("a"):
            href = a.get("href") or ""
            onclick = a.get("onclick") or ""
            combined = f"{href} {onclick}"

            found_idx = extract_board_idx_from_url_or_text(combined)
            if found_idx:
                board_idx = found_idx

            if href and likely_detail_href(href):
                detail_url = urljoin(BASE_URL, href)
                break

            if onclick:
                found_url = extract_url_from_onclick(onclick)
                if found_url:
                    detail_url = urljoin(BASE_URL, found_url)
                    break

        if not board_idx:
            board_idx = extract_board_idx_from_url_or_text(str(row))

        if not detail_url and board_idx:
            detail_url = make_detail_url_from_board_idx(board, board_idx)

        if not detail_url:
            continue

        title, library_label = parse_row_title_and_library(row_text, post_date)

        if not title:
            continue

        items.append(
            ListItem(
                board_name=board["name"],
                source_board=board["source_board"],
                list_url=page_url,
                detail_url=detail_url,
                board_idx=board_idx,
                source_library_label=library_label,
                title=title,
                post_date=post_date,
            )
        )

    if not items:
        for a in soup.find_all("a"):
            href = a.get("href") or ""
            onclick = a.get("onclick") or ""
            text = normalize_space(a.get_text(" ", strip=True))

            if not text:
                continue

            board_idx = extract_board_idx_from_url_or_text(f"{href} {onclick}")
            if not board_idx:
                continue

            detail_url = urljoin(BASE_URL, href) if href else None

            if not detail_url:
                found_url = extract_url_from_onclick(onclick)
                detail_url = urljoin(BASE_URL, found_url) if found_url else None

            if not detail_url:
                detail_url = make_detail_url_from_board_idx(board, board_idx)

            row_text = normalize_space(a.parent.get_text(" ", strip=True) if a.parent else text)
            post_date = parse_date(row_text)
            title = text

            items.append(
                ListItem(
                    board_name=board["name"],
                    source_board=board["source_board"],
                    list_url=page_url,
                    detail_url=detail_url,
                    board_idx=board_idx,
                    source_library_label=None,
                    title=title,
                    post_date=post_date,
                )
            )

    unique: dict[str, ListItem] = {}
    for item in items:
        key = item.board_idx or item.detail_url
        unique[key] = item

    return list(unique.values())


def extract_attachment_urls(soup: BeautifulSoup, detail_url: str) -> list[str]:
    urls: list[str] = []

    for a in soup.find_all("a"):
        href = a.get("href") or ""
        if not href:
            continue

        parsed = urlparse(href)
        path = parsed.path.lower()
        _, ext = os.path.splitext(path)
        text = normalize_space(a.get_text(" ", strip=True)).lower()

        if ext in ATTACHMENT_EXTENSIONS or "첨부" in text or "다운로드" in text:
            urls.append(urljoin(detail_url, href))

    for img in soup.find_all("img"):
        src = img.get("src") or ""
        if src:
            urls.append(urljoin(detail_url, src))

    return sorted(set(urls))


def extract_detail_body_text(soup: BeautifulSoup) -> str:
    selectors = [
        ".board-view",
        ".bbs-view",
        ".view",
        ".view_cont",
        ".view-content",
        ".board_view",
        ".contents",
        "#contents",
        "article",
        "main",
    ]

    candidates: list[str] = []

    for selector in selectors:
        for node in soup.select(selector):
            text = normalize_space(node.get_text(" ", strip=True))
            if len(text) > 50:
                candidates.append(text)

    if candidates:
        return max(candidates, key=len)

    return normalize_space(soup.get_text(" ", strip=True))


def has_attachment_dependency_risk(
    body_text: str,
    attachment_urls: list[str],
    min_body_chars: int,
) -> bool:
    if not attachment_urls:
        return False

    body = normalize_space(body_text)
    has_date = bool(parse_date(body))
    has_program_keywords = any(
        kw in body
        for kw in [
            "운영",
            "일시",
            "기간",
            "대상",
            "신청",
            "접수",
            "모집",
            "장소",
            "강좌",
            "프로그램",
            "행사",
            "상영",
        ]
    )

    if len(body) < min_body_chars:
        return True

    if not has_date or not has_program_keywords:
        return True

    return False


def fetch_detail(
    session: requests.Session,
    item: ListItem,
    allow_attachment_dependent: bool,
    min_body_chars: int,
    sleep_seconds: float,
) -> DetailPayload:
    time.sleep(sleep_seconds)

    try:
        html = fetch_html(session, item.detail_url)
    except requests.RequestException as exc:
        return DetailPayload(
            item=item,
            body_text="",
            attachment_urls=[],
            skipped_reason=f"detail_fetch_failed: {exc}",
        )

    soup = BeautifulSoup(html, "html.parser")
    body_text = extract_detail_body_text(soup)
    attachment_urls = extract_attachment_urls(soup, item.detail_url)

    if not allow_attachment_dependent and has_attachment_dependency_risk(
        body_text=body_text,
        attachment_urls=attachment_urls,
        min_body_chars=min_body_chars,
    ):
        return DetailPayload(
            item=item,
            body_text=body_text,
            attachment_urls=attachment_urls,
            skipped_reason="attachment_dependent_or_body_insufficient",
        )

    return DetailPayload(
        item=item,
        body_text=body_text,
        attachment_urls=attachment_urls,
        skipped_reason=None,
    )


def load_library_pk_map(path: Optional[str]) -> dict[str, int]:
    if not path:
        return {}

    with open(path, "r", encoding="utf-8") as f:
        data = json.load(f)

    if isinstance(data, dict) and "records" in data:
        data = data["records"]

    result: dict[str, int] = {}

    for obj in data:
        if not isinstance(obj, dict):
            continue

        if "fields" in obj:
            fields = obj.get("fields") or {}
            pk = obj.get("pk") or obj.get("id")
        else:
            fields = obj
            pk = obj.get("pk") or obj.get("id")

        if pk is None:
            continue

        name = (
            fields.get("name")
            or fields.get("library_name")
            or fields.get("도서관명")
            or fields.get("source_library_name")
        )
        sigungu = fields.get("sigungu") or fields.get("시군구명")

        if not name:
            continue

        keys = {
            normalize_name(str(name)),
            normalize_name(str(name).replace("부산광역시립", "")),
        }

        if sigungu:
            keys.add(f"{normalize_name(str(name))}|{normalize_name(str(sigungu))}")

        short = normalize_name(str(name))

        alias_rules = [
            ("시민", "시민"),
            ("주례열린", "주례열린"),
            ("동래읍성", "동래읍성"),
            ("안락누리", "안락누리"),
            ("해운대인문학", "해운대인문학"),
            ("부산진구어린이청소년", "부산진구어린이"),
            ("중앙", "중앙"),
            ("해운대", "해운대"),
            ("구포", "구포"),
            ("부산영어", "부산영어"),
        ]

        for needle, alias in alias_rules:
            if needle in short:
                keys.add(alias)

        for key in keys:
            if key:
                result.setdefault(key, int(pk))

    return result


def match_library_pk(
    library_map: dict[str, int],
    source_library_name: Optional[str],
    source_sigungu: Optional[str] = None,
    fallback_label: Optional[str] = None,
) -> Optional[int]:
    if not library_map:
        return None

    candidates = []

    for value in [source_library_name, fallback_label]:
        if value:
            candidates.append(normalize_name(value))
            if source_sigungu:
                candidates.append(f"{normalize_name(value)}|{normalize_name(source_sigungu)}")

    for key in candidates:
        if key in library_map:
            return library_map[key]

    for key in candidates:
        if len(key) <= 2:
            continue

        for lib_key, pk in library_map.items():
            if "|" in lib_key:
                continue

            if key in lib_key or lib_key in key:
                return pk

    return None


def build_extraction_prompt(payload: DetailPayload) -> str:
    item = payload.item
    body = payload.body_text[:8000]

    return f"""
다음 부산도서관포털 게시글에서 문화프로그램 정보를 추출하세요.

규칙:
- 한 게시글 안에 운영 기간이 다른 프로그램이 여러 개 있으면 배열 원소를 여러 개로 나누세요.
- 운영 기간이 같고 회차만 여러 개인 경우 하나로 합치세요.
- 게시글에 명시되지 않은 날짜/대상/신청 여부는 추론하지 말고 null 또는 []로 두세요.
- 모집 안내가 아니라 단순 공지/전시 결과/첨부만 있는 게시물이며 본문만으로 프로그램 정보가 부족하면 []를 반환하세요.
- category_code는 다음 중 하나만 사용하세요:
  lecture_humanities, reading_writing, culture_art, experience_education, exhibition, other
- target_codes는 다음 중에서만 고르세요:
  infant, elementary, teen, adult, senior, family, all
- 날짜는 YYYY-MM-DD 형식으로만 출력하세요.
- application_status, operation_status는 출력하지 마세요. 수집 스크립트가 재계산합니다.
- source_sido는 기본적으로 "부산광역시"로 두세요.
- source_sigungu는 명시되어 있거나 도서관명에서 확실할 때만 채우고, 아니면 null입니다.
- source_library_name은 게시글의 도서관명 또는 목록의 도서관 라벨을 최대한 사용하세요.
- 영화상영 게시판의 영화 상영도 category_code는 culture_art로 분류하세요.

출력 JSON 형식:
[
  {{
    "source_sido": "부산광역시",
    "source_sigungu": null,
    "source_library_name": "도서관명",
    "title": "프로그램명",
    "category_code": "reading_writing",
    "target_text": "원문 대상",
    "target_codes": ["adult"],
    "application_required": true,
    "application_start_date": "2026-06-01",
    "application_end_date": "2026-06-09",
    "operation_start_date": "2026-06-10",
    "operation_end_date": "2026-06-24"
  }}
]

목록 정보:
- 게시판: {item.source_board}
- 목록 도서관 라벨: {item.source_library_label}
- 목록 제목: {item.title}
- 등록일: {item.post_date}
- 원문 URL: {item.detail_url}

본문:
{body}
""".strip()


def parse_json_from_model(content: str) -> Any:
    content = content.strip()

    content = re.sub(r"^```(?:json)?", "", content).strip()
    content = re.sub(r"```$", "", content).strip()

    try:
        return json.loads(content)
    except json.JSONDecodeError:
        pass

    array_start = content.find("[")
    array_end = content.rfind("]")

    if array_start != -1 and array_end != -1 and array_end > array_start:
        try:
            return json.loads(content[array_start : array_end + 1])
        except json.JSONDecodeError:
            pass

    obj_start = content.find("{")
    obj_end = content.rfind("}")

    if obj_start != -1 and obj_end != -1 and obj_end > obj_start:
        try:
            return json.loads(content[obj_start : obj_end + 1])
        except json.JSONDecodeError:
            pass

    return []


def normalize_nullable(value: Any) -> Optional[str]:
    if value is None:
        return None

    text = normalize_space(str(value))

    if not text or text.lower() in {"null", "none", "없음", "-"}:
        return None

    return text


def normalize_date_string(value: Any) -> Optional[str]:
    if not value:
        return None

    if isinstance(value, str):
        value = value.strip()

        try:
            return dt.date.fromisoformat(value[:10]).isoformat()
        except ValueError:
            return parse_date(value)

    return None


def clean_ai_program(obj: dict[str, Any]) -> Optional[dict[str, Any]]:
    title = normalize_space(str(obj.get("title") or ""))

    if not title:
        return None

    category = obj.get("category_code") or "other"
    if category not in CATEGORY_CODES:
        category = "other"

    target_codes = obj.get("target_codes") or []
    if not isinstance(target_codes, list):
        target_codes = []

    target_codes = [code for code in target_codes if code in TARGET_CODES]

    application_required = obj.get("application_required")
    if application_required not in [True, False, None]:
        application_required = None

    return {
        "source_sido": normalize_nullable(obj.get("source_sido")) or "부산광역시",
        "source_sigungu": normalize_nullable(obj.get("source_sigungu")),
        "source_library_name": normalize_nullable(obj.get("source_library_name")),
        "title": title,
        "category_code": category,
        "target_text": normalize_nullable(obj.get("target_text")),
        "target_codes": target_codes,
        "application_required": application_required,
        "application_start_date": normalize_date_string(obj.get("application_start_date")),
        "application_end_date": normalize_date_string(obj.get("application_end_date")),
        "operation_start_date": normalize_date_string(obj.get("operation_start_date")),
        "operation_end_date": normalize_date_string(obj.get("operation_end_date")),
    }


def call_gms_extract(
    payload: DetailPayload,
    model: str,
    base_url: str,
    api_key: str,
    timeout: int = 40,
) -> list[dict[str, Any]]:
    url = f"{base_url.rstrip('/')}/chat/completions"

    headers = {
        "Content-Type": "application/json",
        "Authorization": f"Bearer {api_key}",
    }

    request_body = {
        "model": model,
        "messages": [
            {
                "role": "developer",
                "content": (
                    "너는 공공도서관 문화프로그램 게시글을 Django 모델 필드용 JSON으로 "
                    "구조화하는 데이터 정제기다. 반드시 근거가 있는 정보만 추출한다. "
                    "불확실하면 null 또는 빈 배열을 사용한다. 설명 없이 JSON만 출력한다."
                ),
            },
            {
                "role": "user",
                "content": build_extraction_prompt(payload),
            },
        ],
    }

    response = requests.post(url, headers=headers, json=request_body, timeout=timeout)
    response.raise_for_status()

    data = response.json()
    content = data["choices"][0]["message"]["content"]

    parsed = parse_json_from_model(content)

    if isinstance(parsed, dict):
        parsed = parsed.get("programs", [])

    if not isinstance(parsed, list):
        return []

    cleaned = []

    for obj in parsed:
        if not isinstance(obj, dict):
            continue

        cleaned_obj = clean_ai_program(obj)

        if cleaned_obj:
            cleaned.append(cleaned_obj)

    return cleaned


def make_fixture_object(
    ai_obj: dict[str, Any],
    payload: DetailPayload,
    library_pk: Optional[int],
    fixture_model: str,
    fixture_library_field: str,
    provider_code: str,
    collected_at: str,
    pk: Optional[int] = None,
) -> dict[str, Any]:
    item = payload.item

    operation_start = ai_obj.get("operation_start_date")
    operation_end = ai_obj.get("operation_end_date")

    external_key_basis = "|".join(
        [
            provider_code,
            item.board_idx or "",
            item.detail_url,
            ai_obj.get("title") or "",
            operation_start or "",
            operation_end or "",
        ]
    )

    external_program_key = sha256_text(external_key_basis, 32)

    content_hash_basis = "|".join(
        [
            item.detail_url,
            item.title,
            payload.body_text,
            json.dumps(ai_obj, ensure_ascii=False, sort_keys=True),
        ]
    )

    fields = {
        fixture_library_field: library_pk,
        "source_sido": ai_obj.get("source_sido"),
        "source_sigungu": ai_obj.get("source_sigungu"),
        "source_library_name": ai_obj.get("source_library_name") or item.source_library_label,
        "provider_code": provider_code,
        "external_program_key": external_program_key,
        "title": ai_obj.get("title"),
        "category_code": ai_obj.get("category_code"),
        "target_text": ai_obj.get("target_text"),
        "target_codes": ai_obj.get("target_codes") or [],
        "application_required": ai_obj.get("application_required"),
        "application_start_date": ai_obj.get("application_start_date"),
        "application_end_date": ai_obj.get("application_end_date"),
        "application_status": calculate_application_status(
            ai_obj.get("application_required"),
            ai_obj.get("application_start_date"),
            ai_obj.get("application_end_date"),
        ),
        "operation_start_date": operation_start,
        "operation_end_date": operation_end,
        "operation_status": calculate_operation_status(operation_start, operation_end),
        "source_board": item.source_board,
        "source_url": item.detail_url,
        "post_date": item.post_date,
        "collected_at": collected_at,
        "content_hash": sha256_text(content_hash_basis),
        "is_visible": True,
        "deleted_at": None,
        "created_at": collected_at,
        "updated_at": collected_at,
    }

    obj = {
        "model": fixture_model,
        "fields": fields,
    }

    if pk is not None:
        obj["pk"] = pk

    return obj


def crawl_board_list_items(
    session: requests.Session,
    board: dict[str, str],
    post_start_date: dt.date,
    post_end_date: dt.date,
    max_pages: int,
    sleep_seconds: float,
) -> list[ListItem]:
    all_items: list[ListItem] = []
    seen_keys: set[str] = set()

    passed_target_range = False

    for page in range(1, max_pages + 1):
        page_url = set_query_param(board["url"], viewPage=page)
        print(f"[LIST] {board['name']} page={page} {page_url}", file=sys.stderr)

        try:
            html = fetch_html(session, page_url)
        except requests.RequestException as exc:
            print(f"[WARN] list fetch failed: {exc}", file=sys.stderr)
            break

        items = extract_list_items_from_page(board, html, page_url)

        if not items:
            print(f"[WARN] no items parsed on page {page}", file=sys.stderr)
            break

        page_min_date: Optional[dt.date] = None
        page_has_in_range = False

        for item in items:
            post_date = parse_iso_date(item.post_date)

            if not post_date:
                continue

            if page_min_date is None or post_date < page_min_date:
                page_min_date = post_date

            # 게시일 기준 특정 기간 필터
            if not (post_start_date <= post_date <= post_end_date):
                continue

            page_has_in_range = True

            key = item.board_idx or item.detail_url
            if key in seen_keys:
                continue

            seen_keys.add(key)
            all_items.append(item)

        # 게시판이 최신순이라고 가정:
        # 현재 페이지의 가장 오래된 게시일이 목표 시작일보다 작으면,
        # 다음 페이지는 더 오래된 글일 가능성이 높으므로 중단.
        if page_min_date and page_min_date < post_start_date:
            passed_target_range = True

        print(
            f"[INFO] {board['name']} page={page} "
            f"parsed={len(items)} in_range={page_has_in_range} page_min_date={page_min_date}",
            file=sys.stderr,
        )

        if passed_target_range:
            print(f"[INFO] passed target post date range. stop board={board['name']}", file=sys.stderr)
            break

        time.sleep(sleep_seconds)

    return all_items


def write_json(path: str, data: Any) -> None:
    os.makedirs(os.path.dirname(path) or ".", exist_ok=True)

    with open(path, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)


def main() -> None:
    load_dotenv()

    parser = argparse.ArgumentParser()

    parser.add_argument("--output", default="programs/fixtures/programs.json")
    parser.add_argument("--library-fixture", default=None)
    parser.add_argument("--fixture-model", default="programs.program")
    parser.add_argument("--fixture-library-field", default="library")
    parser.add_argument("--provider-code", default="busan_library_portal")

    parser.add_argument(
        "--post-start-date",
        required=True,
        help="게시일 기준 수집 시작일. 예: 2026-06-01",
    )
    parser.add_argument(
        "--post-end-date",
        required=True,
        help="게시일 기준 수집 종료일. 예: 2026-06-30",
    )

    parser.add_argument("--max-pages", type=int, default=30)
    parser.add_argument("--sleep", type=float, default=0.4)
    parser.add_argument("--min-body-chars", type=int, default=180)
    parser.add_argument("--allow-attachment-dependent", action="store_true")
    parser.add_argument("--keep-unmatched-library", action="store_true")
    parser.add_argument("--with-pk", action="store_true")
    parser.add_argument("--start-pk", type=int, default=1)
    parser.add_argument("--raw-log", default="programs/fixtures/programs_raw_log.json")

    args = parser.parse_args()

    post_start_date = dt.date.fromisoformat(args.post_start_date)
    post_end_date = dt.date.fromisoformat(args.post_end_date)

    if post_start_date > post_end_date:
        raise ValueError("--post-start-date는 --post-end-date보다 늦을 수 없습니다.")

    api_key = os.getenv("GMS_API_KEY")
    base_url = os.getenv(
        "GMS_OPENAI_BASE_URL",
        "https://gms.ssafy.io/gmsapi/api.openai.com/v1",
    )
    model = os.getenv("GMS_MODEL", "gpt-5-nano")

    if not api_key:
        raise RuntimeError("GMS_API_KEY가 없습니다. .env에 GMS_API_KEY를 설정하세요.")

    collected_at = iso_now_kst()

    session = get_session()
    library_map = load_library_pk_map(args.library_fixture)

    raw_log: list[dict[str, Any]] = []
    fixture_objects: list[dict[str, Any]] = []
    seen_external_keys: set[str] = set()

    print(f"[INFO] post_start_date={post_start_date}", file=sys.stderr)
    print(f"[INFO] post_end_date={post_end_date}", file=sys.stderr)
    print(f"[INFO] GMS model={model}", file=sys.stderr)

    list_items: list[ListItem] = []

    for board in DEFAULT_BOARDS:
        items = crawl_board_list_items(
            session=session,
            board=board,
            post_start_date=post_start_date,
            post_end_date=post_end_date,
            max_pages=args.max_pages,
            sleep_seconds=args.sleep,
        )

        list_items.extend(items)

        print(f"[INFO] {board['name']} matched list items={len(items)}", file=sys.stderr)

    print(f"[INFO] total matched list items={len(list_items)}", file=sys.stderr)

    pk_counter = args.start_pk

    for idx, item in enumerate(list_items, start=1):
        print(f"[DETAIL] {idx}/{len(list_items)} {item.source_board} | {item.title}", file=sys.stderr)

        detail = fetch_detail(
            session=session,
            item=item,
            allow_attachment_dependent=args.allow_attachment_dependent,
            min_body_chars=args.min_body_chars,
            sleep_seconds=args.sleep,
        )

        log_entry = {
            "source_board": item.source_board,
            "title": item.title,
            "source_library_label": item.source_library_label,
            "post_date": item.post_date,
            "detail_url": item.detail_url,
            "board_idx": item.board_idx,
            "attachment_urls": detail.attachment_urls,
            "skipped_reason": detail.skipped_reason,
            "ai_program_count": 0,
        }

        if detail.skipped_reason:
            raw_log.append(log_entry)
            print(f"[SKIP] {detail.skipped_reason}", file=sys.stderr)
            continue

        try:
            ai_programs = call_gms_extract(
                payload=detail,
                model=model,
                base_url=base_url,
                api_key=api_key,
            )
        except Exception as exc:
            log_entry["skipped_reason"] = f"gms_failed: {exc}"
            raw_log.append(log_entry)
            print(f"[SKIP] gms_failed: {exc}", file=sys.stderr)
            continue

        log_entry["ai_program_count"] = len(ai_programs)

        if not ai_programs:
            log_entry["skipped_reason"] = "no_program_extracted"
            raw_log.append(log_entry)
            print("[SKIP] no_program_extracted", file=sys.stderr)
            continue

        for ai_obj in ai_programs:
            source_library_name = ai_obj.get("source_library_name") or item.source_library_label

            library_pk = match_library_pk(
                library_map=library_map,
                source_library_name=source_library_name,
                source_sigungu=ai_obj.get("source_sigungu"),
                fallback_label=item.source_library_label,
            )

            if library_pk is None and not args.keep_unmatched_library:
                raw_log.append(
                    {
                        **log_entry,
                        "skipped_reason": "library_unmatched",
                        "ai_program": ai_obj,
                    }
                )
                print(f"[SKIP] library_unmatched: {source_library_name}", file=sys.stderr)
                continue

            fixture_obj = make_fixture_object(
                ai_obj=ai_obj,
                payload=detail,
                library_pk=library_pk,
                fixture_model=args.fixture_model,
                fixture_library_field=args.fixture_library_field,
                provider_code=args.provider_code,
                collected_at=collected_at,
                pk=pk_counter if args.with_pk else None,
            )

            external_key = fixture_obj["fields"]["external_program_key"]

            if external_key in seen_external_keys:
                continue

            seen_external_keys.add(external_key)
            fixture_objects.append(fixture_obj)

            if args.with_pk:
                pk_counter += 1

        raw_log.append(log_entry)

    write_json(args.output, fixture_objects)
    write_json(args.raw_log, raw_log)

    print(f"[DONE] fixture={args.output} count={len(fixture_objects)}", file=sys.stderr)
    print(f"[DONE] raw_log={args.raw_log} count={len(raw_log)}", file=sys.stderr)


if __name__ == "__main__":
    main()