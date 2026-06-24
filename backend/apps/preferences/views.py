from rest_framework.permissions import AllowAny
from rest_framework.response import Response
from rest_framework.views import APIView

from apps.preferences.regions import get_busan_region_options
from apps.preferences.serializers import (
    PreferencePurposeOptionSerializer,
    PreferenceTagOptionSerializer,
)
from apps.recommendations.models import Purpose
from apps.tags.models import Tag


class PreferenceOptionsAPIView(APIView):
    permission_classes = (AllowAny,)

    def get(self, request):
        purposes = Purpose.objects.filter(
            is_active=True,
            is_profile_selectable=True,
        ).order_by("display_order", "code")
        tags = Tag.objects.filter(
            is_active=True,
            is_profile_selectable=True,
        ).order_by("display_order", "code")

        return Response(
            {
                "purposes": PreferencePurposeOptionSerializer(purposes, many=True).data,
                "regions": get_busan_region_options(),
                "tags": PreferenceTagOptionSerializer(tags, many=True).data,
            }
        )
