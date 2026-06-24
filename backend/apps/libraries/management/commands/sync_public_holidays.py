from django.core.management.base import BaseCommand, CommandError
from django.utils import timezone

from apps.libraries.services_public_holidays import sync_public_holiday_year


class Command(BaseCommand):
    help = "Sync Korean public holidays from the public data API."

    def add_arguments(self, parser):
        parser.add_argument("--year", type=int, help="Sync a single year.")
        parser.add_argument("--start-year", type=int, help="First year to sync, inclusive.")
        parser.add_argument("--end-year", type=int, help="Last year to sync, inclusive.")

    def handle(self, *args, **options):
        years = resolve_years(options)
        has_failure = False

        for year in years:
            result = sync_public_holiday_year(year)
            if result.is_complete:
                self.stdout.write(
                    self.style.SUCCESS(
                        f"{year}: complete, holidays={result.holiday_count}, "
                        f"created={result.created_count}, updated={result.updated_count}, "
                        f"deleted={result.deleted_count}, sync_run_id={result.sync_run_id}"
                    )
                )
            else:
                has_failure = True
                failed_months = ",".join(f"{month:02d}" for month in sorted(result.failed_months))
                self.stdout.write(
                    self.style.WARNING(
                        f"{year}: incomplete, synced_month_count={result.synced_month_count}, "
                        f"failed_months={failed_months or '-'}, sync_run_id={result.sync_run_id}"
                    )
                )

        if has_failure:
            raise CommandError("One or more public holiday sync targets were incomplete.")


def resolve_years(options):
    year = options.get("year")
    start_year = options.get("start_year")
    end_year = options.get("end_year")

    if year and (start_year or end_year):
        raise CommandError("--year cannot be used with --start-year or --end-year.")
    if year:
        validate_year(year)
        return [year]

    if start_year or end_year:
        if not start_year or not end_year:
            raise CommandError("--start-year and --end-year must be provided together.")
        validate_year(start_year)
        validate_year(end_year)
        if start_year > end_year:
            raise CommandError("--start-year must be less than or equal to --end-year.")
        return list(range(start_year, end_year + 1))

    current_year = timezone.localdate().year
    return [current_year, current_year + 1]


def validate_year(year):
    if year < 1900 or year > 2100:
        raise CommandError("year must be between 1900 and 2100.")
