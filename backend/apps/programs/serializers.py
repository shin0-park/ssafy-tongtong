from rest_framework import serializers

from .models import Program


class ProgramLibrarySummarySerializer(serializers.Serializer):
    id = serializers.IntegerField()
    name = serializers.CharField()
    sigungu = serializers.CharField()


class ProgramTagSummarySerializer(serializers.Serializer):
    id = serializers.IntegerField(source="tag.id")
    code = serializers.CharField(source="tag.code")
    label = serializers.CharField(source="tag.label")


class ProgramListSerializer(serializers.ModelSerializer):
    library = ProgramLibrarySummarySerializer(read_only=True)
    category = serializers.CharField(source="category_code", read_only=True)
    category_display = serializers.CharField(source="get_category_code_display", read_only=True)
    target = serializers.JSONField(source="target_codes", read_only=True)
    target_display = serializers.CharField(source="target_text", read_only=True)
    application_status_display = serializers.CharField(source="get_application_status_display", read_only=True)
    operation_status_display = serializers.CharField(source="get_operation_status_display", read_only=True)

    class Meta:
        model = Program
        fields = (
            "id",
            "title",
            "library",
            "category",
            "category_display",
            "target",
            "target_display",
            "application_required",
            "application_start_date",
            "application_end_date",
            "application_status",
            "application_status_display",
            "operation_start_date",
            "operation_end_date",
            "operation_status",
            "operation_status_display",
            "source_board",
            "source_url",
            "post_date",
        )


class ProgramDetailSerializer(ProgramListSerializer):
    tags = serializers.SerializerMethodField()

    class Meta(ProgramListSerializer.Meta):
        fields = ProgramListSerializer.Meta.fields + (
            "source_sido",
            "source_sigungu",
            "source_library_name",
            "provider_code",
            "external_program_key",
            "collected_at",
            "tags",
        )

    def get_tags(self, obj):
        tag_links = getattr(obj, "active_tag_links", None)
        if tag_links is None:
            tag_links = obj.tag_links.filter(is_active=True).select_related("tag")
        return ProgramTagSummarySerializer(tag_links, many=True).data
