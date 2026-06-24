from rest_framework import serializers

from apps.recommendations.models import Purpose
from apps.tags.models import Tag


class PreferencePurposeOptionSerializer(serializers.ModelSerializer):
    class Meta:
        model = Purpose
        fields = ("code", "label", "description", "display_order")


class PreferenceTagOptionSerializer(serializers.ModelSerializer):
    class Meta:
        model = Tag
        fields = ("code", "label", "tag_group", "description", "display_order")
