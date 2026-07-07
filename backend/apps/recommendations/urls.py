from django.urls import path

from apps.recommendations.views import HomePersonalRecommendationsAPIView, HomeRecommendationsAPIView


app_name = "recommendations"

urlpatterns = [
    path("", HomeRecommendationsAPIView.as_view(), name="home"),
    path("personal-recommendations/", HomePersonalRecommendationsAPIView.as_view(), name="home-personal-recommendations"),
]
