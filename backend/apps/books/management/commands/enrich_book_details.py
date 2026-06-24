import json
import time
from pathlib import Path

from django.core.management.base import BaseCommand, CommandError

from apps.books.services import apply_book_detail, get_book_detail_candidates
from apps.integrations.data4library import Data4LibraryAPIError, Data4LibraryClient, Data4LibraryConfigurationError


class Command(BaseCommand):
    help = "Enrich local Book records with Data4Library srchDtlList."

    def add_arguments(self, parser):
        parser.add_argument("--source", choices=("popular", "saved", "all"), default="popular")
        parser.add_argument("--daily-budget", type=self.parse_positive_int, default=80)
        parser.add_argument("--limit", type=self.parse_positive_int, default=80)
        parser.add_argument("--only-missing-description", action="store_true")
        parser.add_argument("--min-refetch-days", type=self.parse_non_negative_int, default=30)
        parser.add_argument("--dry-run", action="store_true")
        parser.add_argument("--sleep", type=float, default=0.3)
        parser.add_argument("--output-json")

    def handle(self, *args, **options):
        if options["sleep"] < 0:
            raise CommandError("--sleep must be greater than or equal to 0.")

        call_limit = min(options["daily_budget"], options["limit"])
        candidates = get_book_detail_candidates(
            source=options["source"],
            limit=call_limit,
            only_missing_description=options["only_missing_description"],
            min_refetch_days=options["min_refetch_days"],
        )
        stats = {
            "candidates": len(candidates),
            "api_call_limit": call_limit,
            "called": 0,
            "updated": 0,
            "skipped": 0,
            "failed": 0,
        }
        report = []

        if options["dry_run"]:
            for book in candidates:
                report.append(serialize_candidate(book, "would_call", []))
            self.stdout.write(
                "candidates={candidates} api_call_limit={api_call_limit} called=0 updated=0 skipped=0 failed=0".format(
                    **stats
                )
            )
            self.stdout.write("dry-run: srchDtlList was not called and database writes were skipped.")
            write_output_if_requested(options["output_json"], stats, report, self)
            return

        client = Data4LibraryClient(timeout=15)
        for index, book in enumerate(candidates, start=1):
            try:
                detail = client.get_book_detail(book.isbn13, loaninfo=False)
                stats["called"] += 1
            except Data4LibraryConfigurationError as exc:
                raise CommandError("Data4Library API key is not configured.") from exc
            except Data4LibraryAPIError:
                stats["failed"] += 1
                report.append(serialize_candidate(book, "failed", [], "Data4Library API request failed."))
                continue

            if detail is None:
                stats["skipped"] += 1
                report.append(serialize_candidate(book, "skipped", [], "detail_not_found"))
            else:
                changed_fields = apply_book_detail(book, detail)
                if changed_fields:
                    stats["updated"] += 1
                    report.append(serialize_candidate(book, "updated", changed_fields))
                else:
                    stats["skipped"] += 1
                    report.append(serialize_candidate(book, "skipped", []))

            if index < len(candidates):
                time.sleep(options["sleep"])

        self.stdout.write(
            "candidates={candidates} api_call_limit={api_call_limit} called={called} "
            "updated={updated} skipped={skipped} failed={failed}".format(**stats)
        )
        for item in report[:5]:
            self.stdout.write(
                f"[{item['status']}] isbn13={item['isbn13']} title={item['title']} fields={','.join(item['changed_fields']) or '-'}"
            )
        write_output_if_requested(options["output_json"], stats, report, self)

    @staticmethod
    def parse_positive_int(value):
        try:
            parsed = int(value)
        except (TypeError, ValueError) as exc:
            raise CommandError("Expected a positive integer.") from exc
        if parsed <= 0:
            raise CommandError("Expected a positive integer.")
        return parsed

    @staticmethod
    def parse_non_negative_int(value):
        try:
            parsed = int(value)
        except (TypeError, ValueError) as exc:
            raise CommandError("Expected a non-negative integer.") from exc
        if parsed < 0:
            raise CommandError("Expected a non-negative integer.")
        return parsed


def serialize_candidate(book, status, changed_fields, reason=""):
    return {
        "status": status,
        "isbn13": book.isbn13,
        "title": book.title,
        "local_book_id": book.id,
        "description_present": bool(book.description),
        "metadata_fetched_at": book.metadata_fetched_at,
        "changed_fields": changed_fields,
        "reason": reason,
    }


def write_output_if_requested(path, stats, report, command):
    if not path:
        return
    output_path = Path(path)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(
        json.dumps({"stats": stats, "results": report}, ensure_ascii=False, indent=2, default=str),
        encoding="utf-8",
    )
    command.stdout.write(f"output-json: {path}")
