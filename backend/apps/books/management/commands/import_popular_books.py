import json
import time
from datetime import datetime
from pathlib import Path

from django.core.management.base import BaseCommand, CommandError

from apps.books.services import (
    upsert_book_basic_from_data4library,
    upsert_popular_snapshot_and_items,
)
from apps.integrations.data4library import Data4LibraryAPIError, Data4LibraryClient, Data4LibraryConfigurationError


class Command(BaseCommand):
    help = "Import popular books from Data4Library loanItemSrch."

    def add_arguments(self, parser):
        parser.add_argument("--start-date", required=True)
        parser.add_argument("--end-date", required=True)
        parser.add_argument("--region", default="21")
        parser.add_argument("--page-size", type=self.parse_positive_int, default=200)
        parser.add_argument("--max-pages", type=self.parse_positive_int, default=1)
        parser.add_argument("--dry-run", action="store_true")
        parser.add_argument("--sleep", type=float, default=0.3)
        parser.add_argument("--output-json")
        parser.add_argument("--query-label", default="monthly_busan_popular")

    def handle(self, *args, **options):
        if options["sleep"] < 0:
            raise CommandError("--sleep must be greater than or equal to 0.")

        period_start = parse_date(options["start_date"], "--start-date")
        period_end = parse_date(options["end_date"], "--end-date")
        if period_end < period_start:
            raise CommandError("--end-date must be greater than or equal to --start-date.")

        client = Data4LibraryClient(timeout=15)
        stats = {
            "fetched": 0,
            "created": 0,
            "updated": 0,
            "skipped": 0,
            "rejected": 0,
            "snapshot_status": "none",
            "item_created": 0,
            "item_updated": 0,
            "item_skipped": 0,
            "errors": 0,
        }
        report = []
        popular_books = []

        try:
            for page in range(1, options["max_pages"] + 1):
                payload = client.get_popular_books(
                    {
                        "startDt": period_start.strftime("%Y-%m-%d"),
                        "endDt": period_end.strftime("%Y-%m-%d"),
                        "region": options["region"],
                        "pageNo": page,
                        "pageSize": options["page_size"],
                    }
                )
                page_results = payload["results"]
                stats["fetched"] += len(page_results)
                popular_books.extend(page_results)
                for item in page_results:
                    book, status = upsert_book_basic_from_data4library(item.book, dry_run=options["dry_run"])
                    update_status(stats, status)
                    report.append(serialize_report_item(item, status, book))
                if page < options["max_pages"]:
                    time.sleep(options["sleep"])
        except Data4LibraryConfigurationError as exc:
            raise CommandError("Data4Library API key is not configured.") from exc
        except Data4LibraryAPIError as exc:
            raise CommandError(format_api_error(exc)) from exc

        query_params = {
            "startDt": period_start.strftime("%Y-%m-%d"),
            "endDt": period_end.strftime("%Y-%m-%d"),
            "region": options["region"],
            "pageSize": options["page_size"],
            "maxPages": options["max_pages"],
        }
        _, snapshot_status, item_stats = upsert_popular_snapshot_and_items(
            period_start=period_start,
            period_end=period_end,
            region=options["region"],
            query_label=options["query_label"],
            query_params=query_params,
            popular_books=popular_books,
            dry_run=options["dry_run"],
        )
        stats["snapshot_status"] = snapshot_status
        stats["item_created"] = item_stats["created"]
        stats["item_updated"] = item_stats["updated"]
        stats["item_skipped"] = item_stats["skipped"]

        self.stdout.write(
            "fetched={fetched} created={created} updated={updated} skipped={skipped} "
            "rejected={rejected} snapshot={snapshot_status} item_created={item_created} "
            "item_updated={item_updated} item_skipped={item_skipped} errors={errors}".format(**stats)
        )
        if options["dry_run"]:
            self.stdout.write("dry-run: database writes were skipped.")

        for item in report[:5]:
            self.stdout.write(
                f"[{item['status']}] rank={item['rank'] or '-'} isbn13={item['isbn13'] or '-'} title={item['title']}"
            )

        if options["output_json"]:
            write_json_report(options["output_json"], {"stats": stats, "results": report})
            self.stdout.write(f"output-json: {options['output_json']}")

    @staticmethod
    def parse_positive_int(value):
        try:
            parsed = int(value)
        except (TypeError, ValueError) as exc:
            raise CommandError("Expected a positive integer.") from exc
        if parsed <= 0:
            raise CommandError("Expected a positive integer.")
        return parsed


def parse_date(value, option_name):
    try:
        return datetime.strptime(value, "%Y-%m-%d").date()
    except ValueError as exc:
        raise CommandError(f"{option_name} must be YYYY-MM-DD.") from exc


def update_status(stats, status):
    if status in {"created", "would_create"}:
        stats["created"] += 1
    elif status in {"updated", "would_update"}:
        stats["updated"] += 1
    elif status == "rejected":
        stats["rejected"] += 1
    else:
        stats["skipped"] += 1


def serialize_report_item(item, status, book):
    return {
        "status": status,
        "rank": item.rank,
        "isbn13": item.book.isbn13,
        "title": item.book.title,
        "authors_text": item.book.authors_text,
        "publisher": item.book.publisher,
        "publication_year": item.book.publication_year,
        "kdc_class_no": item.book.kdc_class_no,
        "kdc_class_name": item.book.kdc_class_name,
        "cover_image_url": item.book.cover_image_url,
        "source_detail_url": item.book.source_detail_url,
        "loan_count": item.book.loan_count,
        "local_book_id": getattr(book, "id", None),
    }


def write_json_report(path, payload):
    output_path = Path(path)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(json.dumps(payload, ensure_ascii=False, indent=2, default=str), encoding="utf-8")


def format_api_error(exc):
    request_preview = exc.request_preview or {}
    params = request_preview.get("params") or {}
    params_text = ", ".join(f"{key}={value}" for key, value in params.items()) or "-"
    return "\n".join(
        [
            "Data4Library API request failed.",
            f"endpoint: {exc.endpoint or request_preview.get('endpoint') or '-'}",
            f"url_path: {request_preview.get('path') or '-'}",
            f"params: {params_text}",
            f"exception_class: {exc.original_exception_class or exc.__class__.__name__}",
            f"http_status: {exc.status_code if exc.status_code is not None else '-'}",
            f"reason: {exc.reason or '-'}",
            f"response_content_type: {exc.content_type or '-'}",
            f"response_body_preview: {exc.body_preview or '-'}",
            f"json_parse_failed: {exc.json_parse_failed}",
        ]
    )
