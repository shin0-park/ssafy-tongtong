from django.db.models import Prefetch, Q
from rest_framework import generics

from apps.common.pagination import StandardPageNumberPagination

from .models import Library, LibraryClosureRule, LibraryImage, LibraryOpeningHour, LibraryStatisticSnapshot
from .serializers import LibraryDetailSerializer, LibraryListSerializer


class LibraryQueryMixin:
    serializer_class = LibraryListSerializer

    def get_queryset(self):
        queryset = (
            Library.objects.filter(is_active=True)
            .select_related("facility_profile")
            .prefetch_related(
                Prefetch(
                    "statistic_snapshots",
                    queryset=LibraryStatisticSnapshot.objects.filter(is_current=True).order_by("-reference_date", "-id"),
                    to_attr="current_statistic_snapshots",
                ),
                Prefetch(
                    "images",
                    queryset=LibraryImage.objects.filter(is_active=True, is_main=True).select_related("media_asset").order_by("display_order", "id"),
                    to_attr="active_main_images",
                ),
                Prefetch(
                    "opening_hours",
                    queryset=LibraryOpeningHour.objects.filter(is_current=True).order_by("day_type", "day_of_week", "specific_date", "sequence", "id"),
                    to_attr="current_opening_hours",
                ),
                Prefetch(
                    "closure_rules",
                    queryset=LibraryClosureRule.objects.filter(is_current=True).order_by("priority", "id"),
                    to_attr="current_closure_rules",
                ),
            )
            .order_by("name", "id")
        )
        return self.apply_filters(queryset)

    def apply_filters(self, queryset):
        params = self.request.query_params

        query = params.get("q", "").strip()
        if query:
            queryset = queryset.filter(
                Q(name__icontains=query)
                | Q(normalized_name__icontains=query)
                | Q(road_address__icontains=query)
                | Q(normalized_address__icontains=query)
                | Q(sigungu__icontains=query)
                | Q(operating_agency__icontains=query)
            )

        sigungu_values = self.split_query_values(params.get("sigungu"))
        if sigungu_values:
            queryset = queryset.filter(sigungu__in=sigungu_values)

        library_type_values = self.split_query_values(params.get("library_type"))
        if library_type_values:
            queryset = queryset.filter(library_type__in=library_type_values)

        return queryset

    @staticmethod
    def split_query_values(value):
        if not value:
            return []
        return [item.strip() for item in value.split(",") if item.strip()]


class LibraryListAPIView(LibraryQueryMixin, generics.ListAPIView):
    serializer_class = LibraryListSerializer
    pagination_class = StandardPageNumberPagination


class LibraryDetailAPIView(LibraryQueryMixin, generics.RetrieveAPIView):
    serializer_class = LibraryDetailSerializer
    lookup_url_kwarg = "library_id"
