from django.contrib.auth import get_user_model
from django.core.management.base import BaseCommand, CommandError

from apps.preferences.services import rebuild_user_preferences_for_queryset


class Command(BaseCommand):
    help = "Rebuild behavior-based user preference scores."

    def add_arguments(self, parser):
        parser.add_argument("--user-id", type=int)
        parser.add_argument("--all", action="store_true")

    def handle(self, *args, **options):
        user_id = options.get("user_id")
        rebuild_all = options.get("all")
        if bool(user_id) == bool(rebuild_all):
            raise CommandError("Provide exactly one of --user-id or --all.")

        User = get_user_model()
        if user_id:
            queryset = User.objects.filter(pk=user_id, is_active=True).order_by("id")
            if not queryset.exists():
                raise CommandError("Active user not found.")
        else:
            queryset = User.objects.filter(is_active=True).order_by("id")

        stats = rebuild_user_preferences_for_queryset(queryset)
        self.stdout.write(
            "processed={processed} ready={ready} collecting={collecting} "
            "failed={failed} items={items}".format(**stats)
        )
