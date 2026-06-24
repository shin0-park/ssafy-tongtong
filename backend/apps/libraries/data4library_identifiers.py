import json
import re
import time
from dataclasses import asdict, dataclass, field
from decimal import Decimal
from pathlib import Path

from django.db import transaction
from django.utils import timezone

from apps.integrations.data4library import Data4LibraryClient, Data4LibraryLibrary

from .models import Library, LibraryAlias, LibraryExternalIdentifier


PROVIDER_CODE = "data4library"
CODE_TYPE = "lib_code"

MATCH_CONFIDENCE = {
    "exact_name_address": Decimal("1.0000"),
    "normalized_name_address": Decimal("0.9500"),
    "alias_address": Decimal("0.9000"),
    "phone_name": Decimal("0.8500"),
}


@dataclass
class IdentifierImportResult:
    external: dict
    matched_library_id: int | None = None
    matched_library_name: str | None = None
    match_method: str = ""
    match_confidence: str | None = None
    action: str = ""
    warnings: list[str] = field(default_factory=list)
    reject_reason: str = ""
    conflict_reason: str = ""
    candidate_libraries: list[dict] = field(default_factory=list)


def run_import(
    region="21",
    page_size=100,
    dry_run=False,
    limit_pages=None,
    sleep_seconds=0.3,
    output_json=None,
):
    stats = {
        "fetched": 0,
        "matched": 0,
        "created": 0,
        "updated": 0,
        "would_create": 0,
        "would_update": 0,
        "ambiguous": 0,
        "rejected": 0,
        "conflict": 0,
        "warnings": 0,
    }
    results = []

    with transaction.atomic():
        for external_library in iter_external_libraries(
            region=region,
            page_size=page_size,
            limit_pages=limit_pages,
            sleep_seconds=sleep_seconds,
        ):
            stats["fetched"] += 1
            result = process_external_library(external_library, dry_run=dry_run)
            update_stats(stats, result, dry_run=dry_run)
            results.append(asdict(result))

        if dry_run:
            transaction.set_rollback(True)

    if output_json:
        write_output_json(output_json, stats, results)

    return stats, results


def iter_external_libraries(region="21", page_size=100, limit_pages=None, sleep_seconds=0.3):
    client = Data4LibraryClient()
    page = 1
    while True:
        if limit_pages and page > limit_pages:
            break

        payload = client.list_libraries(region=region, page=page, page_size=page_size)
        libraries = payload["results"]
        if not libraries:
            break

        yield from libraries

        if page * page_size >= payload["count"]:
            break

        page += 1
        if sleep_seconds:
            time.sleep(sleep_seconds)


def process_external_library(external_library: Data4LibraryLibrary, dry_run=False):
    result = IdentifierImportResult(external=serialize_external_library(external_library))
    if not external_library.external_library_key:
        result.reject_reason = "missing_lib_code"
        return result
    if not external_library.name:
        result.reject_reason = "missing_lib_name"
        return result

    matched_library, match_method, candidates = match_library(external_library)
    result.candidate_libraries = serialize_candidate_libraries(candidates)
    if not matched_library:
        result.reject_reason = "ambiguous_match" if candidates else "library_not_matched"
        return result

    result.matched_library_id = matched_library.id
    result.matched_library_name = matched_library.name
    result.match_method = match_method
    result.match_confidence = str(MATCH_CONFIDENCE[match_method])

    existing = LibraryExternalIdentifier.objects.filter(
        provider_code=PROVIDER_CODE,
        code_type=CODE_TYPE,
        external_code=external_library.external_library_key,
    ).select_related("library").first()
    if existing and existing.library_id != matched_library.id:
        result.conflict_reason = "external_code_connected_to_different_library"
        result.candidate_libraries = serialize_candidate_libraries([existing.library, matched_library])
        return result

    result.action = "update" if existing else "create"
    if not dry_run:
        upsert_identifier(external_library, matched_library, match_method, existing)
    return result


def match_library(external_library: Data4LibraryLibrary):
    strategies = (
        ("exact_name_address", find_exact_name_address),
        ("normalized_name_address", find_normalized_name_address),
        ("alias_address", find_alias_address),
        ("phone_name", find_phone_name),
    )
    for method, finder in strategies:
        candidates = finder(external_library)
        if len(candidates) == 1:
            return candidates[0], method, candidates
        if len(candidates) > 1:
            return None, method, candidates
    return None, "", []


def find_exact_name_address(external_library):
    if not external_library.address:
        return []
    return list(
        Library.objects.filter(
            is_active=True,
            name=external_library.name,
            road_address=external_library.address,
        ).order_by("id")
    )


def find_normalized_name_address(external_library):
    normalized_name = normalize_name(external_library.name)
    normalized_address = normalize_address(external_library.address)
    if not normalized_name or not normalized_address:
        return []
    return list(
        Library.objects.filter(
            is_active=True,
            normalized_name=normalized_name,
            normalized_address=normalized_address,
        ).order_by("id")
    )


def find_alias_address(external_library):
    normalized_name = normalize_name(external_library.name)
    if not normalized_name or not external_library.address:
        return []
    aliases = (
        LibraryAlias.objects.filter(
            is_active=True,
            normalized_alias_name=normalized_name,
            library__is_active=True,
            library__road_address=external_library.address,
        )
        .select_related("library")
        .order_by("library_id", "id")
    )
    return unique_libraries([alias.library for alias in aliases])


def find_phone_name(external_library):
    phone = normalize_phone(external_library.phone)
    if not phone:
        return []

    normalized_name = normalize_name(external_library.name)
    direct_candidates = []
    if normalized_name:
        direct_candidates = list(
            Library.objects.filter(
                is_active=True,
                normalized_name=normalized_name,
            ).order_by("id")
        )

    alias_candidates = []
    if normalized_name:
        aliases = (
            LibraryAlias.objects.filter(
                is_active=True,
                normalized_alias_name=normalized_name,
                library__is_active=True,
            )
            .select_related("library")
            .order_by("library_id", "id")
        )
        alias_candidates = [alias.library for alias in aliases]

    candidates = [
        library
        for library in unique_libraries([*direct_candidates, *alias_candidates])
        if normalize_phone(library.phone) == phone
    ]
    return candidates


def upsert_identifier(external_library, library, match_method, existing=None):
    now = timezone.now()
    defaults = {
        "library": library,
        "external_name": external_library.name,
        "external_address": external_library.address,
        "match_method": match_method,
        "match_confidence": MATCH_CONFIDENCE[match_method],
        "last_fetched_at": now,
        "is_active": True,
    }
    if existing:
        for field_name, value in defaults.items():
            setattr(existing, field_name, value)
        if not existing.first_seen_at:
            existing.first_seen_at = now
        existing.save(update_fields=[*defaults, "first_seen_at", "updated_at"])
        return existing, False

    return LibraryExternalIdentifier.objects.create(
        provider_code=PROVIDER_CODE,
        code_type=CODE_TYPE,
        external_code=external_library.external_library_key,
        first_seen_at=now,
        **defaults,
    ), True


def update_stats(stats, result, dry_run=False):
    if result.warnings:
        stats["warnings"] += 1
    if result.conflict_reason:
        stats["conflict"] += 1
        return
    if result.reject_reason:
        if result.reject_reason == "ambiguous_match":
            stats["ambiguous"] += 1
        else:
            stats["rejected"] += 1
        return
    if result.matched_library_id:
        stats["matched"] += 1
    if result.action == "create":
        stats["would_create" if dry_run else "created"] += 1
    elif result.action == "update":
        stats["would_update" if dry_run else "updated"] += 1


def serialize_external_library(external_library):
    return {
        "provider_code": PROVIDER_CODE,
        "external_library_key": external_library.external_library_key or None,
        "name": external_library.name or None,
        "address": external_library.address or None,
        "homepage_url": external_library.homepage_url or None,
        "phone": external_library.phone or None,
        "latitude": external_library.latitude or None,
        "longitude": external_library.longitude or None,
        "closed": external_library.closed or None,
        "operating_time": external_library.operating_time or None,
        "book_count": external_library.book_count,
    }


def serialize_candidate_libraries(candidates):
    return [
        {
            "id": library.id,
            "name": library.name,
            "sigungu": library.sigungu,
            "road_address": library.road_address,
            "phone": library.phone or None,
        }
        for library in unique_libraries(candidates)
    ]


def unique_libraries(libraries):
    seen = set()
    unique = []
    for library in libraries:
        if library.id in seen:
            continue
        seen.add(library.id)
        unique.append(library)
    return unique


def normalize_name(value):
    return re.sub(r"\s+", "", str(value or "").strip())


def normalize_address(value):
    return re.sub(r"\s+", "", str(value or "").strip())


def normalize_phone(value):
    return re.sub(r"\D+", "", str(value or ""))


def write_output_json(path, stats, results):
    output_path = Path(path)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(
        json.dumps({"stats": stats, "results": results}, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )
