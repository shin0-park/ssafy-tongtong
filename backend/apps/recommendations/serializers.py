from rest_framework import serializers

from apps.libraries.serializers import LibraryListSerializer


class RecommendationLibrarySerializer(LibraryListSerializer):
    recommendation_reason = serializers.CharField(read_only=True)
    ai_rank = serializers.SerializerMethodField()
    ai_confidence = serializers.SerializerMethodField()
    matched_priority_tags = serializers.SerializerMethodField()

    class Meta(LibraryListSerializer.Meta):
        fields = LibraryListSerializer.Meta.fields + (
            "recommendation_reason",
            "ai_rank",
            "ai_confidence",
            "matched_priority_tags",
        )

    def get_ai_rank(self, obj):
        return getattr(obj, "ai_rank", None)

    def get_ai_confidence(self, obj):
        confidence = getattr(obj, "ai_confidence", None)
        return confidence if confidence is not None else None

    def get_matched_priority_tags(self, obj):
        return getattr(obj, "matched_priority_tags", [])
