from django.db.models import Prefetch
from django.utils import timezone

from apps.integrations.data4library import Data4LibraryBook
from apps.libraries.models import Library, LibraryExternalIdentifier, LibraryImage, LibraryStatisticSnapshot
from apps.libraries.serializers import LibraryListSerializer

from .models import Book


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
        results.append(
            {
                "matched": library is not None,
                "library": LibraryListSerializer(library).data if library else None,
                "external_library": serialize_external_library(holding_library),
                "holding": serialize_external_holding(holding_library),
            }
        )

    return results


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
                queryset=LibraryImage.objects.filter(is_active=True, is_main=True)
                .select_related("media_asset")
                .order_by("display_order", "id"),
                to_attr="active_main_images",
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
