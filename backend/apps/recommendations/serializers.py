from rest_framework import serializers

from apps.libraries.serializers import LibraryListSerializer


class RecommendationLibrarySerializer(LibraryListSerializer):
    recommendation_reason = serializers.CharField(read_only=True)

    class Meta(LibraryListSerializer.Meta):
        fields = LibraryListSerializer.Meta.fields + ("recommendation_reason",)
