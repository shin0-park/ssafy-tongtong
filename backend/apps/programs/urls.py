from django.urls import path

from apps.myoutings.views import ProgramSaveAPIView

from .views import ProgramDetailAPIView, ProgramListAPIView


app_name = "programs"

urlpatterns = [
    path("", ProgramListAPIView.as_view(), name="program-list"),
    path("<int:program_id>/save/", ProgramSaveAPIView.as_view(), name="program-save"),
    path("<int:program_id>/", ProgramDetailAPIView.as_view(), name="program-detail"),
]
