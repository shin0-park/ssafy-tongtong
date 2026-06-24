from django.utils import timezone

from apps.integrations.data4library import Data4LibraryBook

from .models import Book


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
