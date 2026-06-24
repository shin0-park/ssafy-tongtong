import hashlib
import json
import re
import time
from dataclasses import asdict, dataclass, field
from datetime import date
from pathlib import Path
from typing import Iterable
from urllib.parse import parse_qs, urlencode, urljoin, urlparse

import httpx
from bs4 import BeautifulSoup
from django.db import transaction
from django.utils import timezone

from apps.integrations.models import SourceSyncRun, SourceSyncStatus, SourceType
from apps.libraries.models import Library, LibraryAlias

from .models import ApplicationStatus, OperationStatus, Program, ProgramCategory


BUSAN_LIBRARY_PORTAL_BASE_URL = "https://library.busan.go.kr"
BUSAN_LIBRARY_PORTAL_PROVIDER_CODE = "busan_library_portal"
DATE_PATTERN = re.compile(r"(20\d{2})[.\-/년]\s*(\d{1,2})[.\-/월]\s*(\d{1,2})")
DATE_RANGE_PATTERN = re.compile(
    r"(20\d{2}[.\-/년]\s*\d{1,2}[.\-/월]\s*\d{1,2})\s*(?:~|-|부터|∼)\s*"
    r"(20\d{2}[.\-/년]\s*\d{1,2}[.\-/월]\s*\d{1,2})"
)


@dataclass(frozen=True)
class BoardConfig:
    code: str
    source_board: str
    manage_idx: str
    menu_idx: str
    default_category_code: str


@dataclass
class RawProgramPost:
    board: BoardConfig
    library_name: str
    title: str
    source_url: str
    post_date: date | None
    list_period_text: str = ""
    list_place_text: str = ""


@dataclass
class NormalizedProgramPost:
    board: str
    source_board: str
    provider_code: str
    external_program_key: str
    title: str
    source_library_name: str
    source_sido: str
    source_sigungu: str
    category_code: str
    target_text: str
    target_codes: list[str]
    application_required: bool | None
    application_start_date: date | None
    application_end_date: date | None
    application_status: str
    operation_start_date: date | None
    operation_end_date: date | None
    operation_status: str
    source_url: str
    post_date: date | None
    collected_at: str
    content_hash: str
    detail_text: str
    matched_library_id: int | None = None
    warnings: list[str] = field(default_factory=list)
    reject_reason: str = ""


BOARD_CONFIGS = {
    "course": BoardConfig(
        code="course",
        source_board="강좌신청",
        manage_idx="595",
        menu_idx="67",
        default_category_code=ProgramCategory.LECTURE_HUMANITIES,
    ),
    "reading": BoardConfig(
        code="reading",
        source_board="독서문화행사",
        manage_idx="596",
        menu_idx="17",
        default_category_code=ProgramCategory.READING_WRITING,
    ),
    "event": BoardConfig(
        code="event",
        source_board="영화상영",
        manage_idx="597",
        menu_idx="18",
        default_category_code=ProgramCategory.CULTURE_ART,
    ),
}

PROGRAM_TARGET_RULES = (
    ("for_infant", ("유아", "6~7세", "6-7세", "미취학")),
    ("for_elementary", ("초등", "어린이", "아동")),
    ("for_teen", ("청소년", "중고등", "중학생", "고등학생")),
    ("for_adult", ("성인", "일반", "어른")),
    ("for_senior", ("시니어", "어르신", "노인")),
    ("for_family", ("가족", "부모", "보호자")),
)


class BusanProgramImportService:
    def __init__(self, start_date=None, end_date=None, sleep_seconds=0.3, timeout=10):
        self.start_date = start_date
        self.end_date = end_date
        self.sleep_seconds = sleep_seconds
        self.client = httpx.Client(timeout=timeout, follow_redirects=True)
        self.collected_at = timezone.now()

    def close(self):
        self.client.close()

    def collect(self, board_codes: Iterable[str], limit=None):
        remaining = limit
        for board_code in board_codes:
            board = BOARD_CONFIGS[board_code]
            page = 1
            stop_board = False
            while not stop_board:
                html = self.fetch_list_page(board, page)
                raw_posts = self.parse_list_page(board, html)
                if not raw_posts:
                    break

                for raw_post in raw_posts:
                    if self.end_date and raw_post.post_date and raw_post.post_date > self.end_date:
                        continue
                    if self.start_date and raw_post.post_date and raw_post.post_date < self.start_date:
                        stop_board = True
                        break

                    detail_html = ""
                    detail_text = ""
                    warnings = []
                    if raw_post.source_url:
                        try:
                            detail_html = self.fetch_url(raw_post.source_url)
                            detail_text = extract_visible_text(detail_html)
                        except httpx.HTTPError:
                            warnings.append("detail_fetch_failed")

                    normalized = normalize_program_post(raw_post, detail_text, warnings, self.collected_at)
                    match_library(normalized)
                    yield normalized

                    if remaining is not None:
                        remaining -= 1
                        if remaining <= 0:
                            return

                    time.sleep(self.sleep_seconds)

                page += 1

    def fetch_list_page(self, board, page):
        params = {
            "menu_idx": board.menu_idx,
            "manage_idx": board.manage_idx,
            "board_idx": "0",
            "group_idx": "0",
            "rowCount": "10",
            "viewPage": str(page),
            "search_type": "title+content",
        }
        url = f"{BUSAN_LIBRARY_PORTAL_BASE_URL}/portal/board/index.do?{urlencode(params)}"
        return self.fetch_url(url)

    def fetch_url(self, url):
        response = self.client.get(url)
        response.raise_for_status()
        response.encoding = response.encoding or "utf-8"
        return response.text

    def parse_list_page(self, board, html):
        soup = BeautifulSoup(html, "html.parser")
        rows = []
        for tr in soup.select("tr"):
            cells = [cell.get_text(" ", strip=True) for cell in tr.find_all(["td", "th"])]
            if len(cells) < 4 or not cells[0].strip().isdigit():
                continue

            link = tr.find("a", href=True)
            source_href = link["href"] if link else tr.get("data-href", "")
            source_url = urljoin(BUSAN_LIBRARY_PORTAL_BASE_URL, source_href) if source_href else ""
            if not source_url:
                source_url = find_source_url_from_row(tr)
            rows.append(build_raw_post_from_cells(board, cells, source_url))

        if rows:
            return rows

        return parse_text_fallback_rows(board, soup.get_text("\n", strip=True))


def build_raw_post_from_cells(board, cells, source_url):
    if board.code == "course":
        library_name = safe_cell(cells, 1)
        title = safe_cell(cells, 2)
        period_text = safe_cell(cells, 3)
        post_date = parse_first_date(safe_cell(cells, 4))
    elif board.code == "event":
        library_name = safe_cell(cells, 1)
        title = safe_cell(cells, 2)
        period_text = safe_cell(cells, 3)
        place_text = safe_cell(cells, 4)
        post_date = parse_first_date(safe_cell(cells, 5)) or parse_first_date(cells[-1])
        return RawProgramPost(board, library_name, title, source_url, post_date, period_text, place_text)
    else:
        library_name = safe_cell(cells, 1)
        title = safe_cell(cells, 2)
        post_date = parse_first_date(safe_cell(cells, 3))
        period_text = ""

    return RawProgramPost(board, library_name, title, source_url, post_date, period_text)


def parse_text_fallback_rows(board, text):
    rows = []
    for line in text.splitlines():
        tokens = line.split()
        if len(tokens) < 4 or not tokens[0].isdigit():
            continue
        post_date = parse_first_date(line)
        if not post_date:
            continue
        library_name = tokens[1]
        date_match = DATE_PATTERN.search(line)
        title_segment = line
        if date_match:
            title_segment = line[: date_match.start()].strip()
        title_tokens = title_segment.split()[2:]
        title = " ".join(title_tokens).strip()
        if title:
            rows.append(RawProgramPost(board, library_name, title, "", post_date))
    return rows


def find_source_url_from_row(row):
    html = str(row)
    match = re.search(r"board_idx=(\d+)", html)
    if not match:
        return ""
    return urljoin(BUSAN_LIBRARY_PORTAL_BASE_URL, match.group(0))


def normalize_program_post(raw_post, detail_text, initial_warnings, collected_at):
    warnings = list(initial_warnings)
    source_text = " ".join(
        value
        for value in (raw_post.title, raw_post.list_period_text, raw_post.list_place_text, detail_text)
        if value
    )
    application_start_date = None
    application_end_date = None
    operation_start_date = None
    operation_end_date = None
    application_required = None
    application_status = ""
    operation_status = ""

    if raw_post.board.code == "course":
        application_required = True
        application_start_date, application_end_date = parse_date_range(raw_post.list_period_text)
        if application_end_date:
            application_status = calculate_application_status(application_end_date)
        else:
            warnings.append("application_period_unparsed")
    else:
        application_required = False
        application_status = ApplicationStatus.NOT_REQUIRED

    operation_start_date, operation_end_date = parse_operation_period(source_text)
    if operation_start_date and operation_end_date:
        operation_status = calculate_operation_status(operation_start_date, operation_end_date)
    else:
        warnings.append("operation_period_unparsed")

    category_code = infer_category_code(raw_post.board, source_text)
    target_text = extract_target_text(source_text)
    target_codes = infer_target_codes(target_text or source_text)
    external_program_key = build_external_program_key(raw_post, operation_start_date, operation_end_date)
    content_hash = stable_hash(
        json.dumps(
            {
                "title": raw_post.title,
                "library": raw_post.library_name,
                "source_url": raw_post.source_url,
                "detail_text": detail_text,
            },
            ensure_ascii=False,
            sort_keys=True,
        )
    )

    normalized = NormalizedProgramPost(
        board=raw_post.board.code,
        source_board=raw_post.board.source_board,
        provider_code=BUSAN_LIBRARY_PORTAL_PROVIDER_CODE,
        external_program_key=external_program_key,
        title=raw_post.title.strip(),
        source_library_name=raw_post.library_name.strip(),
        source_sido="부산광역시",
        source_sigungu="",
        category_code=category_code,
        target_text=target_text,
        target_codes=target_codes,
        application_required=application_required,
        application_start_date=application_start_date,
        application_end_date=application_end_date,
        application_status=application_status,
        operation_start_date=operation_start_date,
        operation_end_date=operation_end_date,
        operation_status=operation_status,
        source_url=raw_post.source_url,
        post_date=raw_post.post_date,
        collected_at=collected_at.isoformat(),
        content_hash=content_hash,
        detail_text=detail_text,
        warnings=warnings,
    )
    validate_normalized_post(normalized)
    return normalized


def match_library(normalized):
    if normalized.reject_reason:
        return None

    source_name = normalized.source_library_name.strip()
    if not source_name:
        normalized.reject_reason = "missing_source_library_name"
        return None

    candidate_names = build_library_name_candidates(source_name)
    libraries = Library.objects.filter(is_active=True, name__in=candidate_names).order_by("id")
    library = pick_library(libraries, normalized.source_sigungu)
    if not library:
        aliases = (
            LibraryAlias.objects.filter(
                is_active=True,
                alias_name__in=candidate_names,
                library__is_active=True,
            )
            .select_related("library")
            .order_by("id")
        )
        alias = pick_alias(aliases, normalized.source_sigungu)
        library = alias.library if alias else None

    if not library:
        normalized.reject_reason = "library_not_matched"
        normalized.warnings.append("library_not_matched")
        return None

    normalized.matched_library_id = library.id
    normalized.source_sigungu = library.sigungu
    return library


def upsert_program(normalized):
    if normalized.reject_reason:
        return None, False

    library = Library.objects.get(id=normalized.matched_library_id, is_active=True)
    defaults = {
        "library": library,
        "source_sido": normalized.source_sido,
        "source_sigungu": normalized.source_sigungu,
        "source_library_name": normalized.source_library_name,
        "title": normalized.title,
        "category_code": normalized.category_code,
        "target_text": normalized.target_text,
        "target_codes": normalized.target_codes,
        "application_required": normalized.application_required,
        "application_start_date": normalized.application_start_date,
        "application_end_date": normalized.application_end_date,
        "application_status": normalized.application_status,
        "operation_start_date": normalized.operation_start_date,
        "operation_end_date": normalized.operation_end_date,
        "operation_status": normalized.operation_status,
        "source_board": normalized.source_board,
        "source_url": normalized.source_url,
        "post_date": normalized.post_date,
        "collected_at": timezone.now(),
        "content_hash": normalized.content_hash,
        "is_visible": True,
    }
    return Program.objects.update_or_create(
        provider_code=normalized.provider_code,
        external_program_key=normalized.external_program_key,
        defaults=defaults,
    )


def run_import(board="all", start_date=None, end_date=None, dry_run=False, limit=None, sleep_seconds=0.3, output_json=None):
    board_codes = list(BOARD_CONFIGS) if board == "all" else [board]
    service = BusanProgramImportService(start_date=start_date, end_date=end_date, sleep_seconds=sleep_seconds)
    results = []
    stats = {
        "parsed": 0,
        "created": 0,
        "updated": 0,
        "rejected": 0,
        "warnings": 0,
    }
    sync_run = None
    if not dry_run:
        sync_run = SourceSyncRun.objects.create(
            source_name="busan_library_portal_programs",
            source_type=SourceType.CRAWLER,
            target_domain="program",
            parameters={
                "board": board,
                "start_date": start_date.isoformat() if start_date else None,
                "end_date": end_date.isoformat() if end_date else None,
                "limit": limit,
                "dry_run": dry_run,
            },
        )

    try:
        with transaction.atomic():
            for normalized in service.collect(board_codes, limit=limit):
                stats["parsed"] += 1
                if normalized.warnings:
                    stats["warnings"] += 1
                if normalized.reject_reason:
                    stats["rejected"] += 1
                elif not dry_run:
                    _, created = upsert_program(normalized)
                    if created:
                        stats["created"] += 1
                    else:
                        stats["updated"] += 1

                results.append(normalized_to_report(normalized))

            if dry_run:
                transaction.set_rollback(True)

        if sync_run:
            sync_run.status = SourceSyncStatus.SUCCESS if stats["rejected"] == 0 else SourceSyncStatus.PARTIAL
            sync_run.finished_at = timezone.now()
            sync_run.total_count = stats["parsed"]
            sync_run.success_count = stats["created"] + stats["updated"]
            sync_run.failure_count = stats["rejected"]
            sync_run.warning_count = stats["warnings"]
            sync_run.summary = stats
            sync_run.save()
    except Exception as exc:
        if sync_run:
            sync_run.status = SourceSyncStatus.FAILED
            sync_run.finished_at = timezone.now()
            sync_run.error_message = str(exc)
            sync_run.summary = stats
            sync_run.save()
        raise
    finally:
        service.close()

    if output_json:
        write_output_json(output_json, stats, results)

    return stats, results


def validate_normalized_post(normalized):
    if not normalized.title:
        normalized.reject_reason = "missing_title"
    elif not normalized.source_url:
        normalized.reject_reason = "missing_source_url"
    elif not normalized.external_program_key:
        normalized.reject_reason = "missing_external_program_key"
    if not normalized.category_code:
        normalized.category_code = ProgramCategory.OTHER
        normalized.warnings.append("category_defaulted_to_other")


def infer_category_code(board, text):
    if "전시" in text:
        return ProgramCategory.EXHIBITION
    if any(keyword in text for keyword in ("독서", "글쓰기", "책", "문해력", "하브루타", "그림책")):
        return ProgramCategory.READING_WRITING
    if any(keyword in text for keyword in ("영화", "상영")):
        return ProgramCategory.CULTURE_ART
    if any(keyword in text for keyword in ("체험", "놀이", "요리", "만들기", "창의")):
        return ProgramCategory.EXPERIENCE_EDUCATION
    return board.default_category_code if board.default_category_code in ProgramCategory.values else ProgramCategory.OTHER


def extract_target_text(text):
    chunks = []
    for keyword in ("대상", "유아", "초등", "청소년", "성인", "가족", "어린이", "시니어"):
        if keyword in text:
            chunks.append(keyword)
    return ", ".join(dict.fromkeys(chunks))


def infer_target_codes(text):
    codes = []
    for code, keywords in PROGRAM_TARGET_RULES:
        if any(keyword in text for keyword in keywords) and code not in codes:
            codes.append(code)
    return codes


def parse_operation_period(text):
    labeled_patterns = (
        r"(?:운영|행사|강의|교육|일시|기간)[^\n]{0,20}"
        r"(20\d{2}[.\-/년]\s*\d{1,2}[.\-/월]\s*\d{1,2}\s*(?:~|-|부터|∼)\s*20\d{2}[.\-/년]\s*\d{1,2}[.\-/월]\s*\d{1,2})",
    )
    for pattern in labeled_patterns:
        match = re.search(pattern, text)
        if match:
            parsed = parse_date_range(match.group(1))
            if parsed != (None, None):
                return parsed
    return parse_date_range(text)


def parse_date_range(text):
    match = DATE_RANGE_PATTERN.search(text or "")
    if not match:
        return None, None
    return parse_date(match.group(1)), parse_date(match.group(2))


def parse_first_date(text):
    match = DATE_PATTERN.search(text or "")
    if not match:
        return None
    return parse_date(match.group(0))


def parse_date(value):
    match = DATE_PATTERN.search(value or "")
    if not match:
        return None
    year, month, day = (int(part) for part in match.groups())
    try:
        return date(year, month, day)
    except ValueError:
        return None


def calculate_application_status(application_end_date):
    if timezone.localdate() <= application_end_date:
        return ApplicationStatus.AVAILABLE
    return ApplicationStatus.CLOSED


def calculate_operation_status(operation_start_date, operation_end_date):
    today = timezone.localdate()
    if today < operation_start_date:
        return OperationStatus.UPCOMING
    if today > operation_end_date:
        return OperationStatus.ENDED
    return OperationStatus.ONGOING


def build_external_program_key(raw_post, operation_start_date, operation_end_date):
    board_idx = extract_board_idx(raw_post.source_url)
    if board_idx:
        return f"{raw_post.board.manage_idx}:{board_idx}"
    stable_input = "|".join(
        [
            raw_post.source_url,
            raw_post.title,
            raw_post.library_name,
            operation_start_date.isoformat() if operation_start_date else "",
            operation_end_date.isoformat() if operation_end_date else "",
        ]
    )
    return stable_hash(stable_input)


def extract_board_idx(source_url):
    query = parse_qs(urlparse(source_url).query)
    values = query.get("board_idx") or query.get("boardIdx")
    if values and values[0] and values[0] != "0":
        return values[0]
    match = re.search(r"board_idx[=/](\d+)", source_url or "")
    return match.group(1) if match else ""


def build_library_name_candidates(source_name):
    source_name = source_name.strip()
    candidates = [source_name]
    if source_name and not source_name.endswith("도서관"):
        candidates.append(f"{source_name}도서관")
    return list(dict.fromkeys(candidates))


def pick_library(libraries, sigungu):
    items = list(libraries)
    if not items:
        return None
    if sigungu:
        for library in items:
            if library.sigungu == sigungu:
                return library
    return items[0] if len(items) == 1 else None


def pick_alias(aliases, sigungu):
    items = list(aliases)
    if not items:
        return None
    if sigungu:
        for alias in items:
            if alias.sigungu in ("", sigungu) or alias.library.sigungu == sigungu:
                return alias
    return items[0] if len(items) == 1 else None


def extract_visible_text(html):
    soup = BeautifulSoup(html, "html.parser")
    for tag in soup(["script", "style", "noscript"]):
        tag.decompose()
    main = soup.select_one("#contents, #content, .board_view, .view, .bbs_view, table")
    return (main or soup).get_text("\n", strip=True)


def safe_cell(cells, index):
    return cells[index].strip() if len(cells) > index else ""


def stable_hash(value):
    return hashlib.sha256(value.encode("utf-8")).hexdigest()


def normalized_to_report(normalized):
    data = asdict(normalized)
    for key in ("application_start_date", "application_end_date", "operation_start_date", "operation_end_date", "post_date"):
        if data[key]:
            data[key] = data[key].isoformat()
    data["detail_text"] = data["detail_text"][:1000]
    return data


def write_output_json(path, stats, results):
    output_path = Path(path)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    payload = {
        "stats": stats,
        "results": results,
    }
    output_path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
