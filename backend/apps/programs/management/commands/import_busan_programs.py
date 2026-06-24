from django.core.management.base import BaseCommand, CommandError

from apps.programs.importers import run_import


class Command(BaseCommand):
    help = "Import Busan library portal program posts."

    def add_arguments(self, parser):
        parser.add_argument("--start-date", type=self.parse_date_arg)
        parser.add_argument("--end-date", type=self.parse_date_arg)
        parser.add_argument(
            "--board",
            choices=("reading", "course", "event", "all"),
            default="all",
        )
        parser.add_argument("--dry-run", action="store_true")
        parser.add_argument("--limit", type=self.parse_positive_int)
        parser.add_argument("--sleep", type=float, default=0.3)
        parser.add_argument("--output-json")

    def handle(self, *args, **options):
        sleep_seconds = options["sleep"]
        if sleep_seconds < 0:
            raise CommandError("--sleep must be greater than or equal to 0.")

        stats, results = run_import(
            board=options["board"],
            start_date=options["start_date"],
            end_date=options["end_date"],
            dry_run=options["dry_run"],
            limit=options["limit"],
            sleep_seconds=sleep_seconds,
            output_json=options["output_json"],
        )

        self.stdout.write(
            "parsed={parsed} created={created} updated={updated} rejected={rejected} warnings={warnings}".format(
                **stats
            )
        )
        if options["dry_run"]:
            self.stdout.write("dry-run: database writes were skipped.")

        for item in results[:5]:
            status = "reject" if item["reject_reason"] else "ready"
            self.stdout.write(
                f"[{status}] {item['source_board']} | {item['source_library_name']} | "
                f"{item['title']} | library_id={item['matched_library_id']} | "
                f"warnings={','.join(item['warnings']) or '-'}"
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

    @staticmethod
    def parse_date_arg(value):
        from datetime import date

        try:
            return date.fromisoformat(value)
        except ValueError as exc:
            raise CommandError("Date arguments must use YYYY-MM-DD format.") from exc
