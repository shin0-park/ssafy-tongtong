from django.contrib.auth import get_user_model
from django.test import TestCase, override_settings
from django.utils import timezone
from rest_framework.test import APIClient
from unittest.mock import patch

from apps.accounts.models import UserPreferredTag
from apps.libraries.models import (
    Library,
    LibraryDailySchedule,
    LibraryFacilityProfile,
    LibraryTag,
    LibraryTagSourceMethod,
    LibraryType,
    ScheduleStatus,
)
from apps.recommendations.providers import RecommendationProviderError, RuleBasedFallbackRecommendationProvider
from apps.tags.models import Tag, TagGroup, TagSemanticKind


class HomeRecommendationV4APITestCase(TestCase):
    def setUp(self):
        self.client = APIClient()
        self.user = get_user_model().objects.create_user(
            email="recommend@example.com",
            password="password",
            nickname="추천러",
        )
        self.tag = Tag.objects.create(
            code="facility_lounge",
            label="휴게공간",
            semantic_kind=TagSemanticKind.OBJECTIVE,
            tag_group=TagGroup.FACILITY,
            is_profile_selectable=True,
            is_filterable=True,
        )
        self.library = self.create_open_library("AI추천도서관", "사상구")
        LibraryFacilityProfile.objects.create(library=self.library, has_lounge=True)
        LibraryTag.objects.create(
            library=self.library,
            tag=self.tag,
            source_method=LibraryTagSourceMethod.FACILITY_RULE,
            source_field="has_lounge",
        )
        UserPreferredTag.objects.create(user=self.user, tag=self.tag)

    def create_open_library(self, name, sigungu, is_active=True):
        library = Library.objects.create(
            name=name,
            normalized_name=name,
            sido="부산광역시",
            sigungu=sigungu,
            library_type=LibraryType.PUBLIC,
            road_address=f"부산광역시 {sigungu} 테스트로 1",
            normalized_address=f"부산광역시 {sigungu} 테스트로 1",
            is_active=is_active,
        )
        LibraryDailySchedule.objects.create(
            library=library,
            date=timezone.localdate(),
            status=ScheduleStatus.OPEN,
            open_time="09:00",
            close_time="18:00",
            rule_version="test",
            generated_at=timezone.now(),
        )
        return library

    @override_settings(
        AI_RECOMMENDATION_ENABLED=True,
        AI_RECOMMENDATION_PROVIDER="mock",
        AI_RECOMMENDATION_FALLBACK_PROVIDER="rule_based",
        GMS_API_KEY="",
    )
    def test_home_personal_recommendations_use_mock_without_gms_key(self):
        self.client.force_authenticate(self.user)

        response = self.client.get("/api/v1/home/")

        self.assertEqual(response.status_code, 200)
        personal = response.data["personal_recommendations"]
        self.assertTrue(personal["available"])
        self.assertFalse(personal["fallback_used"])
        self.assertEqual(personal["provider"], "mock")
        self.assertEqual(personal["mode"], "ai")
        self.assertEqual(personal["priority_tags"][0]["code"], "facility_lounge")
        item = personal["items"][0]
        self.assertEqual(item["ai_rank"], 1)
        self.assertIsNotNone(item["ai_confidence"])
        self.assertEqual(item["matched_priority_tags"][0]["code"], "facility_lounge")
        self.assertTrue(item["recommendation_reason"])

    @override_settings(
        AI_RECOMMENDATION_ENABLED=True,
        AI_RECOMMENDATION_PROVIDER="mock",
        AI_RECOMMENDATION_FALLBACK_PROVIDER="rule_based",
    )
    def test_invalid_library_id_and_tag_code_are_removed_from_provider_output(self):
        class InvalidItemProvider:
            provider_code = "invalid_item"

            def plan_preferences(self, context):
                return {
                    "priority_tags": [{"code": "facility_lounge", "weight": 1}],
                    "priority_purposes": [],
                    "preferred_regions": [],
                    "weights": {},
                }

            def rerank_libraries(self, bundle):
                return {
                    "items": [
                        {
                            "library_id": 999999,
                            "rank": 1,
                            "confidence": 1,
                            "matched_priority_tags": ["missing_tag"],
                            "recommendation_reason": "없는 도서관",
                        },
                        {
                            "library_id": self_outer.library.id,
                            "rank": 2,
                            "confidence": 0.9,
                            "matched_priority_tags": ["facility_lounge", "missing_tag"],
                            "recommendation_reason": "검증 가능한 추천",
                        },
                    ]
                }

        self_outer = self
        self.client.force_authenticate(self.user)
        with patch("apps.recommendations.services.get_provider", return_value=InvalidItemProvider()):
            response = self.client.get("/api/v1/home/")

        personal = response.data["personal_recommendations"]
        self.assertTrue(personal["available"])
        self.assertFalse(personal["fallback_used"])
        self.assertEqual(len(personal["items"]), 1)
        self.assertEqual(personal["items"][0]["id"], self.library.id)
        self.assertEqual(
            personal["items"][0]["matched_priority_tags"],
            [{"code": "facility_lounge", "label": "휴게공간"}],
        )

    @override_settings(
        AI_RECOMMENDATION_ENABLED=True,
        AI_RECOMMENDATION_PROVIDER="mock",
        AI_RECOMMENDATION_FALLBACK_PROVIDER="rule_based",
    )
    def test_malformed_provider_output_falls_back_to_rule_based(self):
        class MalformedProvider:
            provider_code = "malformed"

            def plan_preferences(self, context):
                return []

            def rerank_libraries(self, bundle):
                return {"items": []}

        self.client.force_authenticate(self.user)
        with patch(
            "apps.recommendations.services.get_provider",
            side_effect=[MalformedProvider(), RuleBasedFallbackRecommendationProvider()],
        ):
            response = self.client.get("/api/v1/home/")

        personal = response.data["personal_recommendations"]
        self.assertTrue(personal["available"])
        self.assertTrue(personal["fallback_used"])
        self.assertEqual(personal["provider"], "rule_based")
        self.assertEqual(personal["mode"], "fallback")
        self.assertEqual(personal["items"][0]["ai_rank"], 1)

    @override_settings(
        AI_RECOMMENDATION_ENABLED=True,
        AI_RECOMMENDATION_PROVIDER="mock",
        AI_RECOMMENDATION_FALLBACK_PROVIDER="rule_based",
    )
    def test_provider_receives_public_candidate_bundle_without_orm_object(self):
        captured_candidates = []

        class InspectingProvider:
            provider_code = "inspecting"

            def plan_preferences(self, context):
                return {
                    "priority_tags": [{"code": "facility_lounge", "weight": 1}],
                    "priority_purposes": [],
                    "preferred_regions": [],
                    "weights": {},
                }

            def rerank_libraries(self, bundle):
                captured_candidates.extend(bundle["candidates"])
                return {
                    "items": [
                        {
                            "library_id": bundle["candidates"][0]["library_id"],
                            "rank": 1,
                            "confidence": 0.9,
                            "matched_priority_tags": ["facility_lounge"],
                            "recommendation_reason": "검증 가능한 추천",
                        }
                    ]
                }

        self.client.force_authenticate(self.user)
        with patch("apps.recommendations.services.get_provider", return_value=InspectingProvider()):
            response = self.client.get("/api/v1/home/")

        self.assertEqual(response.status_code, 200)
        self.assertTrue(captured_candidates)
        candidate = captured_candidates[0]
        self.assertNotIn("_library", candidate)
        self.assertIn("book_count_bucket", candidate["stats"])
        self.assertIn("reading_seat_count_bucket", candidate["stats"])
        self.assertEqual(candidate["operation"], {"open_today": True})

    @override_settings(
        AI_RECOMMENDATION_ENABLED=True,
        AI_RECOMMENDATION_PROVIDER="gms_chat",
        AI_RECOMMENDATION_FALLBACK_PROVIDER="missing_provider",
    )
    def test_unknown_fallback_provider_returns_safe_empty_response(self):
        self.client.force_authenticate(self.user)

        response = self.client.get("/api/v1/home/")

        self.assertEqual(response.status_code, 200)
        personal = response.data["personal_recommendations"]
        self.assertFalse(personal["available"])
        self.assertEqual(personal["items"], [])
        self.assertEqual(personal["priority_tags"], [])
        self.assertTrue(personal["fallback_used"])
        self.assertEqual(personal["provider"], "missing_provider")
        self.assertEqual(personal["mode"], "fallback_failed")

    @override_settings(
        AI_RECOMMENDATION_ENABLED=True,
        AI_RECOMMENDATION_PROVIDER="gms_chat",
        AI_RECOMMENDATION_FALLBACK_PROVIDER="rule_based",
    )
    def test_fallback_provider_exception_returns_safe_empty_response(self):
        class BrokenFallbackProvider:
            provider_code = "broken_fallback"

            def plan_preferences(self, context):
                raise RecommendationProviderError("fallback exploded")

            def rerank_libraries(self, bundle):
                return {"items": []}

        self.client.force_authenticate(self.user)
        with patch(
            "apps.recommendations.services.get_provider",
            side_effect=[
                RecommendationProviderError("primary exploded"),
                BrokenFallbackProvider(),
            ],
        ):
            response = self.client.get("/api/v1/home/")

        self.assertEqual(response.status_code, 200)
        personal = response.data["personal_recommendations"]
        self.assertFalse(personal["available"])
        self.assertEqual(personal["items"], [])
        self.assertEqual(personal["priority_tags"], [])
        self.assertTrue(personal["fallback_used"])
        self.assertEqual(personal["provider"], "rule_based")
        self.assertEqual(personal["mode"], "fallback_failed")

    def test_no_personal_signal_keeps_personal_recommendations_unavailable(self):
        user = get_user_model().objects.create_user(
            email="empty@example.com",
            password="password",
            nickname="빈사용자",
        )
        self.client.force_authenticate(user)

        response = self.client.get("/api/v1/home/")

        self.assertEqual(response.status_code, 200)
        personal = response.data["personal_recommendations"]
        self.assertFalse(personal["available"])
        self.assertEqual(personal["priority_tags"], [])
        self.assertFalse(personal["fallback_used"])
        self.assertEqual(personal["items"], [])
