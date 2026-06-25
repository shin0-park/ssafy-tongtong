import hashlib
import json
from datetime import timedelta

from django.db.models import Max, Prefetch, Q
from django.utils import timezone

from apps.integrations.data4library import Data4LibraryBook, Data4LibraryBookDetail
from apps.libraries.data4library_identifiers import match_library, normalize_address, normalize_name, normalize_phone
from apps.libraries.models import Library, LibraryExternalIdentifier, LibraryImage, LibraryStatisticSnapshot
from apps.libraries.serializers import LibraryListSerializer, library_thumbnail_image_queryset

from .models import Book, PopularBookItem, PopularBookScopeType, PopularBookSnapshot


DATA4LIBRARY_PROVIDER_CODE = "data4library"
DATA4LIBRARY_LIBRARY_CODE_TYPES = ("lib_code", "libCode")


def upsert_book_from_data4library(book_data: Data4LibraryBook):
    if not book_data.isbn13:
        return None

    defaults = {
        "title": book_data.title or book_data.isbn13,
        "authors_text": book_data.authors_text,
        "publisher": book_data.publisher,
        "publication_year": book_data.publication_year,
        "volume": book_data.volume,
        "addition_symbol": book_data.addition_symbol,
        "kdc_class_no": book_data.kdc_class_no,
        "kdc_class_name": book_data.kdc_class_name,
        "cover_image_url": book_data.cover_image_url,
        "source_detail_url": book_data.source_detail_url,
        "provider_code": "data4library",
        "metadata_fetched_at": timezone.now(),
    }
    book, created = Book.objects.get_or_create(
        isbn13=book_data.isbn13,
        defaults=defaults,
    )
    if created:
        return book

    changed_fields = []
    fill_if_empty_fields = (
        "authors_text",
        "publisher",
        "publication_year",
        "volume",
        "addition_symbol",
        "kdc_class_no",
        "kdc_class_name",
        "cover_image_url",
        "source_detail_url",
        "provider_code",
    )
    if not book.title and defaults["title"]:
        book.title = defaults["title"]
        changed_fields.append("title")
    for field in fill_if_empty_fields:
        if not getattr(book, field) and defaults[field]:
            setattr(book, field, defaults[field])
            changed_fields.append(field)

    book.metadata_fetched_at = defaults["metadata_fetched_at"]
    changed_fields.append("metadata_fetched_at")
    book.save(update_fields=changed_fields)
    return book


def upsert_book_basic_from_data4library(book_data: Data4LibraryBook, *, dry_run=False):
    if not book_data.isbn13:
        return None, "rejected"

    defaults = build_book_basic_defaults(book_data)
    try:
        book = Book.objects.get(isbn13=book_data.isbn13)
    except Book.DoesNotExist:
        if dry_run:
            preview = Book(isbn13=book_data.isbn13, **defaults)
            preview.id = None
            return preview, "would_create"
        return Book.objects.create(isbn13=book_data.isbn13, **defaults), "created"

    changed_fields = []
    if not book.title and defaults["title"]:
        book.title = defaults["title"]
        changed_fields.append("title")

    fill_if_empty_fields = (
        "authors_text",
        "publisher",
        "publication_year",
        "volume",
        "addition_symbol",
        "kdc_class_no",
        "kdc_class_name",
        "cover_image_url",
        "source_detail_url",
        "provider_code",
    )
    for field in fill_if_empty_fields:
        if not getattr(book, field) and defaults[field]:
            setattr(book, field, defaults[field])
            changed_fields.append(field)

    if not changed_fields:
        return book, "skipped"
    if dry_run:
        return book, "would_update"
    book.save(update_fields=changed_fields)
    return book, "updated"


def build_book_basic_defaults(book_data: Data4LibraryBook):
    return {
        "title": book_data.title or book_data.isbn13,
        "authors_text": book_data.authors_text,
        "publisher": book_data.publisher,
        "publication_year": book_data.publication_year,
        "volume": book_data.volume,
        "addition_symbol": book_data.addition_symbol,
        "kdc_class_no": book_data.kdc_class_no,
        "kdc_class_name": book_data.kdc_class_name,
        "cover_image_url": book_data.cover_image_url,
        "source_detail_url": book_data.source_detail_url,
        "provider_code": DATA4LIBRARY_PROVIDER_CODE,
    }


def upsert_popular_snapshot_and_items(
    *,
    period_start,
    period_end,
    region,
    query_label,
    query_params,
    popular_books,
    dry_run=False,
):
    query_hash = build_query_hash(
        {
            "label": query_label,
            "region": region,
            **query_params,
        }
    )
    snapshot_defaults = {
        "provider_code": DATA4LIBRARY_PROVIDER_CODE,
        "scope_type": PopularBookScopeType.REGION if region else PopularBookScopeType.NATIONAL,
        "region_code": str(region or ""),
        "period_start": period_start,
        "period_end": period_end,
        "query_params": {"label": query_label, "region": region, **query_params},
        "query_hash": query_hash,
        "result_count": len(popular_books),
        "fetched_at": timezone.now(),
        "fresh_until": timezone.now() + timedelta(days=7),
    }

    if dry_run:
        exists = PopularBookSnapshot.objects.filter(
            provider_code=DATA4LIBRARY_PROVIDER_CODE,
            query_hash=query_hash,
            period_start=period_start,
            period_end=period_end,
        ).exists()
        return None, "would_update" if exists else "would_create", {"created": 0, "updated": 0, "skipped": 0}

    snapshot, created = PopularBookSnapshot.objects.update_or_create(
        provider_code=DATA4LIBRARY_PROVIDER_CODE,
        query_hash=query_hash,
        period_start=period_start,
        period_end=period_end,
        defaults=snapshot_defaults,
    )

    item_stats = {"created": 0, "updated": 0, "skipped": 0}
    for fallback_rank, popular_book in enumerate(popular_books, start=1):
        book, _ = upsert_book_basic_from_data4library(popular_book.book)
        if book is None:
            continue
        rank = fallback_rank
        item_defaults = {
            "rank": rank,
            "loan_count": popular_book.book.loan_count,
            "source_payload": popular_book.source_payload,
        }
        item, item_created = PopularBookItem.objects.get_or_create(
            snapshot=snapshot,
            book=book,
            defaults=item_defaults,
        )
        if item_created:
            item_stats["created"] += 1
            continue
        if item_has_changed(item, item_defaults):
            for field, value in item_defaults.items():
                setattr(item, field, value)
            item.save(update_fields=list(item_defaults.keys()))
            item_stats["updated"] += 1
        else:
            item_stats["skipped"] += 1

    return snapshot, "created" if created else "updated", item_stats


def item_has_changed(item, defaults):
    return any(getattr(item, field) != value for field, value in defaults.items())


def build_query_hash(query_params):
    encoded = json.dumps(query_params, ensure_ascii=False, sort_keys=True, default=str)
    return hashlib.sha256(encoded.encode("utf-8")).hexdigest()


def apply_book_detail(book: Book, detail: Data4LibraryBookDetail, *, dry_run=False):
    changed_fields = []

    fill_if_empty_fields = {
        "title": detail.title,
        "authors_text": detail.authors_text,
        "publisher": detail.publisher,
        "publication_date": detail.publication_date,
        "publication_year": detail.publication_year,
        "volume": detail.volume,
        "addition_symbol": detail.addition_symbol,
        "kdc_class_no": detail.kdc_class_no,
        "kdc_class_name": detail.kdc_class_name,
        "description": detail.description,
        "cover_image_url": detail.cover_image_url,
        "source_detail_url": detail.source_detail_url,
    }
    for field, value in fill_if_empty_fields.items():
        if not value:
            continue
        if field == "description" and book.description:
            continue
        if not getattr(book, field):
            setattr(book, field, value)
            changed_fields.append(field)

    book.provider_code = DATA4LIBRARY_PROVIDER_CODE
    changed_fields.append("provider_code")
    book.metadata_fetched_at = timezone.now()
    changed_fields.append("metadata_fetched_at")

    changed_fields = list(dict.fromkeys(changed_fields))
    if not dry_run:
        book.save(update_fields=changed_fields)
    return changed_fields


def get_book_detail_candidates(*, source, limit, only_missing_description, min_refetch_days):
    queryset = Book.objects.filter(is_active=True).exclude(isbn13="")

    if source == "popular":
        popular_book_ids = PopularBookItem.objects.values("book_id")
        queryset = queryset.filter(id__in=popular_book_ids).annotate(
            best_rank=Max("popular_items__rank"),
            max_loan_count=Max("popular_items__loan_count"),
        )
    elif source == "saved":
        queryset = queryset.filter(saved_by_users__isnull=False).distinct()
    elif source != "all":
        raise ValueError("source must be one of popular, saved, all.")

    if only_missing_description:
        queryset = queryset.filter(Q(description="") | Q(description__isnull=True))

    if min_refetch_days is not None:
        threshold = timezone.now() - timedelta(days=min_refetch_days)
        queryset = queryset.filter(Q(metadata_fetched_at__isnull=True) | Q(metadata_fetched_at__lt=threshold))

    if source == "popular":
        queryset = queryset.order_by("best_rank", "-max_loan_count", "id")
    else:
        queryset = queryset.order_by("metadata_fetched_at", "id")

    return list(queryset[:limit])


def serialize_data4library_book(book_data, local_book):
    return {
        "isbn13": book_data.isbn13,
        "title": book_data.title,
        "authors_text": book_data.authors_text,
        "publisher": book_data.publisher,
        "publication_year": book_data.publication_year,
        "kdc_class_no": book_data.kdc_class_no,
        "kdc_class_name": book_data.kdc_class_name,
        "cover_image_url": book_data.cover_image_url,
        "source_detail_url": book_data.source_detail_url,
        "loan_count": book_data.loan_count,
        "local_book_id": local_book.id if local_book else None,
    }


def serialize_book_holding_libraries(holding_libraries):
    library_by_external_code = get_library_by_external_code(holding_libraries)
    results = []

    for holding_library in holding_libraries:
        library = library_by_external_code.get(holding_library.external_library_key)
        if library is None:
            library = match_holding_library(holding_library)
        results.append(
            {
                "matched": library is not None,
                "library": LibraryListSerializer(library).data if library else None,
                "external_library": serialize_external_library(holding_library),
                "holding": serialize_external_holding(holding_library),
            }
        )

    return results


def match_holding_library(holding_library):
    matched_library, _, _ = match_library(holding_library)
    if matched_library:
        return matched_library
    candidates = find_holding_library_candidates(holding_library)
    return candidates[0] if len(candidates) == 1 else None


def find_holding_library_candidates(holding_library):
    external_name = normalize_name(holding_library.name)
    external_address = normalize_address(holding_library.address)
    external_phone = normalize_phone(holding_library.phone)
    if not external_name and not external_address and not external_phone:
        return []

    candidates = []
    libraries = Library.objects.filter(is_active=True).only(
        "id",
        "name",
        "normalized_name",
        "normalized_address",
        "phone",
    ).order_by("id")
    for library in libraries:
        if external_phone and normalize_phone(library.phone) != external_phone:
            continue
        if external_name and not names_are_compatible(external_name, library.normalized_name):
            continue
        if external_address and not addresses_are_compatible(external_address, library.normalized_address):
            continue
        candidates.append(library)
    return candidates


def names_are_compatible(external_name, local_name):
    if not external_name or not local_name:
        return False
    return external_name == local_name or external_name.endswith(local_name) or local_name.endswith(external_name)


def addresses_are_compatible(external_address, local_address):
    if not external_address or not local_address:
        return False
    return external_address == local_address or external_address.startswith(local_address) or local_address.startswith(external_address)


def get_library_by_external_code(holding_libraries):
    external_codes = [
        holding_library.external_library_key
        for holding_library in holding_libraries
        if holding_library.external_library_key
    ]
    if not external_codes:
        return {}

    identifiers = (
        LibraryExternalIdentifier.objects.filter(
            provider_code=DATA4LIBRARY_PROVIDER_CODE,
            code_type__in=DATA4LIBRARY_LIBRARY_CODE_TYPES,
            external_code__in=external_codes,
            is_active=True,
            library__is_active=True,
        )
        .select_related("library")
        .order_by("external_code", "-match_confidence", "id")
    )

    external_code_to_library_id = {}
    for identifier in identifiers:
        external_code_to_library_id.setdefault(identifier.external_code, identifier.library_id)

    libraries = get_libraries_for_cards(external_code_to_library_id.values())
    return {
        external_code: libraries.get(library_id)
        for external_code, library_id in external_code_to_library_id.items()
    }


def get_libraries_for_cards(library_ids):
    library_ids = list({library_id for library_id in library_ids if library_id})
    if not library_ids:
        return {}

    libraries = (
        Library.objects.filter(id__in=library_ids, is_active=True)
        .prefetch_related(
            Prefetch(
                "statistic_snapshots",
                queryset=LibraryStatisticSnapshot.objects.filter(is_current=True).order_by("-reference_date", "-id"),
                to_attr="current_statistic_snapshots",
            ),
            Prefetch(
                "images",
                queryset=library_thumbnail_image_queryset(LibraryImage.objects.all()),
                to_attr="thumbnail_images",
            ),
        )
    )
    return {library.id: library for library in libraries}


def serialize_external_library(holding_library):
    return {
        "provider_code": DATA4LIBRARY_PROVIDER_CODE,
        "external_library_key": holding_library.external_library_key or None,
        "name": holding_library.name or None,
        "address": holding_library.address or None,
        "homepage_url": holding_library.homepage_url or None,
        "phone": holding_library.phone or None,
        "latitude": holding_library.latitude or None,
        "longitude": holding_library.longitude or None,
    }


def serialize_external_holding(holding_library):
    return {
        "call_number": holding_library.call_number or None,
        "loan_available": holding_library.loan_available,
        "loan_status": holding_library.loan_status or None,
    }
