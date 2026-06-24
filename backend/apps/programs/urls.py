from django.urls import path

from .views import ProgramDetailAPIView, ProgramListAPIView


app_name = "programs"

urlpatterns = [
    path("", ProgramListAPIView.as_view(), name="program-list"),
    path("<int:program_id>/", ProgramDetailAPIView.as_view(), name="program-detail"),
]
