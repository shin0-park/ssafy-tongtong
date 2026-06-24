from django.urls import path

from apps.preferences.views import PreferenceOptionsAPIView


app_name = "preferences"

urlpatterns = [
    path("options/", PreferenceOptionsAPIView.as_view(), name="preference-options"),
]
