from datetime import date

from django.core.management.base import BaseCommand, CommandError

from apps.libraries.models import Library
from apps.libraries.services_daily_schedules import build_library_daily_schedules


class Command(BaseCommand):
    help = "Build daily operation schedules for libraries."

    def add_arguments(self, parser):
        parser.add_argument("--year", type=int, help="Build schedules for a full year.")
        parser.add_argument("--start-date", help="First date to build, inclusive. Format: YYYY-MM-DD.")
        parser.add_argument("--end-date", help="Last date to build, inclusive. Format: YYYY-MM-DD.")
        parser.add_argument("--library-id", type=int, help="Build schedules for a single active library.")
        parser.add_argument("--dry-run", action="store_true", help="Calculate summary without writing rows.")

    def handle(self, *args, **options):
        start_date, end_date = resolve_date_range(options)
        library_id = options.get("library_id")
        if library_id is not None and not Library.objects.filter(id=library_id, is_active=True).exists():
            raise CommandError(f"Active library not found: {library_id}")

        try:
            stats = build_library_daily_schedules(
                start_date,
                end_date,
                library_id=library_id,
                dry_run=options["dry_run"],
            )
        except ValueError as exc:
            raise CommandError(str(exc)) from exc

        prefix = "dry-run" if stats.dry_run else "written"
        self.stdout.write(
            (
                f"{prefix}: libraries={stats.target_library_count} dates={stats.target_date_count} "
                f"planned={stats.planned_count} written={stats.written_count} "
                f"open={stats.open_count} closed={stats.closed_count} "
                f"unknown={stats.unknown_count} conflicts={stats.conflict_count}"
            )
        )


def resolve_date_range(options):
    year = options.get("year")
    start_date_raw = options.get("start_date")
    end_date_raw = options.get("end_date")

    if not year and not start_date_raw and not end_date_raw:
        raise CommandError("--year or --start-date/--end-date is required.")
    if year and (start_date_raw or end_date_raw):
        raise CommandError("--year cannot be used with --start-date or --end-date.")
    if year:
        validate_year(year)
        return date(year, 1, 1), date(year, 12, 31)

    if not start_date_raw or not end_date_raw:
        raise CommandError("--start-date and --end-date must be provided together.")

    start_date = parse_date(start_date_raw, "--start-date")
    end_date = parse_date(end_date_raw, "--end-date")
    if start_date > end_date:
        raise CommandError("--start-date must be less than or equal to --end-date.")
    return start_date, end_date


def validate_year(year):
    if year < 1900 or year > 2100:
        raise CommandError("year must be between 1900 and 2100.")


def parse_date(value, option_name):
    try:
        return date.fromisoformat(value)
    except (TypeError, ValueError) as exc:
        raise CommandError(f"{option_name} must use YYYY-MM-DD format.") from exc
