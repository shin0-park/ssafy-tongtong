from django.core.management.base import BaseCommand, CommandError

from apps.integrations.data4library import Data4LibraryAPIError, Data4LibraryConfigurationError
from apps.libraries.data4library_identifiers import run_import


class Command(BaseCommand):
    help = "Import Data4Library libCode identifiers for existing libraries."

    def add_arguments(self, parser):
        parser.add_argument("--region", default="21")
        parser.add_argument("--page-size", type=self.parse_positive_int, default=100)
        parser.add_argument("--dry-run", action="store_true")
        parser.add_argument("--limit-pages", type=self.parse_positive_int)
        parser.add_argument("--sleep", type=float, default=0.3)
        parser.add_argument("--output-json")

    def handle(self, *args, **options):
        if options["sleep"] < 0:
            raise CommandError("--sleep must be greater than or equal to 0.")

        try:
            stats, results = run_import(
                region=options["region"],
                page_size=options["page_size"],
                dry_run=options["dry_run"],
                limit_pages=options["limit_pages"],
                sleep_seconds=options["sleep"],
                output_json=options["output_json"],
            )
        except Data4LibraryConfigurationError as exc:
            raise CommandError("Data4Library API key is not configured.") from exc
        except Data4LibraryAPIError as exc:
            raise CommandError(format_api_error(exc)) from exc

        self.stdout.write(
            "fetched={fetched} matched={matched} created={created} updated={updated} "
            "would_create={would_create} would_update={would_update} ambiguous={ambiguous} "
            "rejected={rejected} conflict={conflict} warnings={warnings}".format(**stats)
        )
        if options["dry_run"]:
            self.stdout.write("dry-run: database writes were skipped.")

        for item in results[:5]:
            status = "ready"
            if item["conflict_reason"]:
                status = "conflict"
            elif item["reject_reason"]:
                status = "ambiguous" if item["reject_reason"] == "ambiguous_match" else "reject"
            self.stdout.write(
                f"[{status}] {item['external']['external_library_key']} | "
                f"{item['external']['name']} | library_id={item['matched_library_id']} | "
                f"method={item['match_method'] or '-'} | "
                f"reason={item['reject_reason'] or item['conflict_reason'] or '-'}"
            )

        if options["output_json"]:
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
