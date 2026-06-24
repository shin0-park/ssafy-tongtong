from django.db.models import Q
from rest_framework import generics

from apps.common.pagination import StandardPageNumberPagination

from .models import Program
from .serializers import ProgramDetailSerializer, ProgramListSerializer


class ProgramQueryMixin:
    serializer_class = ProgramListSerializer

    def get_queryset(self):
        queryset = (
            Program.objects.filter(is_visible=True, deleted_at__isnull=True)
            .select_related("library")
            .prefetch_related("tag_links__tag")
            .order_by("-operation_start_date", "title", "id")
        )
        return self.apply_filters(queryset)

    def apply_filters(self, queryset):
        params = self.request.query_params

        query = params.get("q", "").strip()
        if query:
            queryset = queryset.filter(
                Q(title__icontains=query)
                | Q(library__name__icontains=query)
                | Q(source_library_name__icontains=query)
                | Q(source_board__icontains=query)
                | Q(source_url__icontains=query)
            )

        library_id = params.get("library_id", "").strip()
        if library_id:
            queryset = queryset.filter(library_id=library_id)

        sigungu_values = self.split_query_values(params.get("sigungu"))
        if sigungu_values:
            queryset = queryset.filter(library__sigungu__in=sigungu_values)

        category_values = self.split_query_values(params.get("category"))
        if category_values:
            queryset = queryset.filter(category_code__in=category_values)

        target_values = self.split_query_values(params.get("target"))
        if target_values:
            target_query = Q()
            for target_value in target_values:
                target_query |= Q(target_codes__icontains=target_value)
            queryset = queryset.filter(target_query)

        application_status_values = self.split_query_values(params.get("application_status"))
        if application_status_values:
            queryset = queryset.filter(application_status__in=application_status_values)

        operation_status_values = self.split_query_values(params.get("operation_status"))
        if operation_status_values:
            queryset = queryset.filter(operation_status__in=operation_status_values)

        return queryset

    @staticmethod
    def split_query_values(value):
        if not value:
            return []
        return [item.strip() for item in value.split(",") if item.strip()]


class ProgramListAPIView(ProgramQueryMixin, generics.ListAPIView):
    serializer_class = ProgramListSerializer
    pagination_class = StandardPageNumberPagination


class ProgramDetailAPIView(ProgramQueryMixin, generics.RetrieveAPIView):
    serializer_class = ProgramDetailSerializer
    lookup_url_kwarg = "program_id"
