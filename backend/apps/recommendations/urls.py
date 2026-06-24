from django.urls import path

from apps.recommendations.views import HomeRecommendationsAPIView


app_name = "recommendations"

urlpatterns = [
    path("", HomeRecommendationsAPIView.as_view(), name="home"),
]
