from django.db.models import Prefetch, Q
from django.shortcuts import get_object_or_404
from rest_framework import generics
from rest_framework.response import Response
from rest_framework.views import APIView

from apps.common.pagination import StandardPageNumberPagination

from .models import Library, LibraryClosureRule, LibraryDailySchedule, LibraryImage, LibraryOpeningHour, LibraryStatisticSnapshot
from .serializers import LibraryDetailSerializer, LibraryListSerializer, SimilarLibrarySerializer
from .services import (
    apply_advanced_library_filters,
    calculate_similar_libraries,
    collect_operation_prefetch_dates,
    get_holiday_status_target_date,
    library_tag_prefetch,
    parse_limit,
)


class LibraryQueryMixin:
    serializer_class = LibraryListSerializer

    def get_base_queryset(self):
        operation_dates = collect_operation_prefetch_dates(getattr(self.request, "query_params", None))
        return (
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
                Prefetch(
                    "daily_schedules",
                    queryset=LibraryDailySchedule.objects.filter(date__in=operation_dates).order_by("date", "id"),
                    to_attr="prefetched_daily_schedules",
                ),
                library_tag_prefetch,
            )
            .order_by("name", "id")
        )

    def get_queryset(self):
        queryset = self.get_base_queryset()
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

        return apply_advanced_library_filters(queryset, params)

    @staticmethod
    def split_query_values(value):
        if not value:
            return []
        return [item.strip() for item in value.split(",") if item.strip()]


class LibraryListAPIView(LibraryQueryMixin, generics.ListAPIView):
    serializer_class = LibraryListSerializer
    pagination_class = StandardPageNumberPagination

    def get_serializer_context(self):
        context = super().get_serializer_context()
        params = self.request.query_params
        if "holiday_status" in params or "holiday_date" in params:
            context["holiday_operation_date"] = get_holiday_status_target_date(params)
        return context


class LibraryDetailAPIView(LibraryQueryMixin, generics.RetrieveAPIView):
    serializer_class = LibraryDetailSerializer
    lookup_url_kwarg = "library_id"

    def get_queryset(self):
        return self.get_base_queryset()


class LibrarySimilarAPIView(LibraryQueryMixin, APIView):
    def get(self, request, library_id):
        limit = parse_limit(request.query_params.get("limit"), default=3, maximum=10)
        base_queryset = self.get_base_queryset()
        base_library = get_object_or_404(base_queryset, pk=library_id)
        candidates = list(base_queryset.exclude(pk=base_library.pk))
        similar_libraries = calculate_similar_libraries(base_library, candidates, limit)
        return Response(
            {
                "count": len(similar_libraries),
                "results": SimilarLibrarySerializer(similar_libraries, many=True).data,
            }
        )
