from rest_framework.permissions import AllowAny
from rest_framework.response import Response
from rest_framework.views import APIView

from apps.recommendations.serializers import RecommendationLibrarySerializer
from apps.recommendations.services import (
    build_home_payload,
    parse_coordinate,
    purpose_payload,
)


class HomeRecommendationsAPIView(APIView):
    permission_classes = (AllowAny,)

    def get(self, request):
        payload = build_home_payload(
            user=request.user,
            lat=parse_coordinate(request.query_params.get("lat")),
            lng=parse_coordinate(request.query_params.get("lng")),
        )
        return Response(
            {
                "today_recommendations": self.serialize_today(payload["today"]),
                "theme_recommendations": self.serialize_themes(payload["themes"]),
                "personal_recommendations": self.serialize_personal(payload["personal"]),
            }
        )

    def serialize_today(self, today):
        return {
            "theme": today["theme"],
            "items": RecommendationLibrarySerializer(today["items"], many=True).data,
        }

    def serialize_themes(self, themes):
        return [
            {
                "purpose": purpose_payload(recommendation["purpose"]),
                "items": RecommendationLibrarySerializer(recommendation["items"], many=True).data,
            }
            for recommendation in themes
        ]

    def serialize_personal(self, personal):
        return {
            "available": personal["available"],
            "reason": personal["reason"],
            "items": RecommendationLibrarySerializer(personal["items"], many=True).data,
        }
