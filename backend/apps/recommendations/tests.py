import json

from django.contrib.auth import get_user_model
from django.test import TestCase, override_settings
from django.utils import timezone
from rest_framework.test import APIClient
from unittest.mock import patch

from apps.integrations.gms import GMSClientError, request_chat_json
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
from apps.recommendations.services import (
    build_personal_recommendations_v4,
    build_stat_max,
    get_candidate_libraries,
)
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
        GMS_API_KEY="test-key",
        GMS_OPENAI_BASE_URL="https://api.openai.example/v1",
    )
    def test_request_chat_json_uses_max_completion_tokens_payload_key(self):
        captured_payload = {}

        class FakeResponse:
            def __enter__(self):
                return self

            def __exit__(self, exc_type, exc, traceback):
                return False

            def read(self):
                return json.dumps(
                    {
                        "choices": [
                            {
                                "message": {
                                    "content": json.dumps({"ok": True}),
                                }
                            }
                        ]
                    }
                ).encode("utf-8")

        def fake_urlopen(http_request, timeout):
            captured_payload.update(json.loads(http_request.data.decode("utf-8")))
            return FakeResponse()

        with patch("apps.integrations.gms.request.urlopen", side_effect=fake_urlopen):
            result = request_chat_json(
                [{"role": "user", "content": '{"ok": true}'}],
                model="gpt-5-mini",
                timeout_seconds=5,
                max_tokens=40,
            )

        self.assertEqual(result, {"ok": True})
        self.assertEqual(captured_payload["max_completion_tokens"], 40)
        self.assertNotIn("max_tokens", captured_payload)
        self.assertNotIn("temperature", captured_payload)
        self.assertEqual(captured_payload["response_format"], {"type": "json_object"})

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
                            "evidence_codes": ["tag:missing_tag"],
                            "recommendation_reason": "없는 도서관",
                        },
                        {
                            "library_id": self_outer.library.id,
                            "rank": 2,
                            "confidence": 0.9,
                            "matched_priority_tags": ["facility_lounge", "missing_tag"],
                            "evidence_codes": ["tag:facility_lounge", "tag:missing_tag"],
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
                            "evidence_codes": ["tag:facility_lounge"],
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
        self.assertIn("tag:facility_lounge", candidate["allowed_evidence_codes"])
        self.assertIn("operation:open_today", candidate["allowed_evidence_codes"])

    @override_settings(
        AI_RECOMMENDATION_ENABLED=True,
        AI_RECOMMENDATION_PROVIDER="mock",
        AI_RECOMMENDATION_FALLBACK_PROVIDER="rule_based",
    )
    def test_valid_evidence_codes_keep_provider_reason(self):
        class ValidEvidenceProvider:
            provider_code = "valid_evidence"

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
                            "library_id": bundle["candidates"][0]["library_id"],
                            "rank": 1,
                            "confidence": 0.9,
                            "matched_priority_tags": ["facility_lounge"],
                            "evidence_codes": ["tag:facility_lounge"],
                            "recommendation_reason": "휴게공간 선호가 반영된 추천이에요.",
                        }
                    ]
                }

        self.client.force_authenticate(self.user)
        with patch("apps.recommendations.services.get_provider", return_value=ValidEvidenceProvider()):
            response = self.client.get("/api/v1/home/")

        item = response.data["personal_recommendations"]["items"][0]
        self.assertEqual(item["recommendation_reason"], "휴게공간 선호가 반영된 추천이에요.")

    @override_settings(
        AI_RECOMMENDATION_ENABLED=True,
        AI_RECOMMENDATION_PROVIDER="mock",
        AI_RECOMMENDATION_FALLBACK_PROVIDER="rule_based",
    )
    def test_invalid_evidence_code_replaces_provider_reason(self):
        class InvalidEvidenceProvider:
            provider_code = "invalid_evidence"

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
                            "library_id": bundle["candidates"][0]["library_id"],
                            "rank": 1,
                            "confidence": 0.9,
                            "matched_priority_tags": ["facility_lounge"],
                            "evidence_codes": ["metric:made_up"],
                            "recommendation_reason": "없는 사실로 만든 추천 문장입니다.",
                        }
                    ]
                }

        self.client.force_authenticate(self.user)
        with patch("apps.recommendations.services.get_provider", return_value=InvalidEvidenceProvider()):
            response = self.client.get("/api/v1/home/")

        item = response.data["personal_recommendations"]["items"][0]
        self.assertNotEqual(item["recommendation_reason"], "없는 사실로 만든 추천 문장입니다.")
        self.assertIn("휴게공간", item["recommendation_reason"])

    @override_settings(
        AI_RECOMMENDATION_ENABLED=True,
        AI_RECOMMENDATION_PROVIDER="mock",
        AI_RECOMMENDATION_FALLBACK_PROVIDER="rule_based",
    )
    def test_empty_evidence_codes_replace_provider_reason(self):
        class EmptyEvidenceProvider:
            provider_code = "empty_evidence"

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
                            "library_id": bundle["candidates"][0]["library_id"],
                            "rank": 1,
                            "confidence": 0.9,
                            "matched_priority_tags": ["facility_lounge"],
                            "evidence_codes": [],
                            "recommendation_reason": "근거 없이 만든 추천 문장입니다.",
                        }
                    ]
                }

        self.client.force_authenticate(self.user)
        with patch("apps.recommendations.services.get_provider", return_value=EmptyEvidenceProvider()):
            response = self.client.get("/api/v1/home/")

        item = response.data["personal_recommendations"]["items"][0]
        self.assertNotEqual(item["recommendation_reason"], "근거 없이 만든 추천 문장입니다.")
        self.assertIn("휴게공간", item["recommendation_reason"])

    @override_settings(
        AI_RECOMMENDATION_ENABLED=True,
        AI_RECOMMENDATION_PROVIDER="mock",
        AI_RECOMMENDATION_FALLBACK_PROVIDER="rule_based",
    )
    def test_abnormal_reason_type_uses_fallback_reason(self):
        class AbnormalReasonProvider:
            provider_code = "abnormal_reason"

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
                            "library_id": bundle["candidates"][0]["library_id"],
                            "rank": 1,
                            "confidence": 0.9,
                            "matched_priority_tags": ["facility_lounge"],
                            "evidence_codes": ["tag:facility_lounge"],
                            "recommendation_reason": {"bad": "type"},
                        }
                    ]
                }

        self.client.force_authenticate(self.user)
        with patch("apps.recommendations.services.get_provider", return_value=AbnormalReasonProvider()):
            response = self.client.get("/api/v1/home/")

        item = response.data["personal_recommendations"]["items"][0]
        self.assertIn("휴게공간", item["recommendation_reason"])

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

    @override_settings(
        AI_RECOMMENDATION_ENABLED=True,
        AI_RECOMMENDATION_PROVIDER="gms_chat",
        AI_RECOMMENDATION_FALLBACK_PROVIDER="rule_based",
        GMS_API_KEY="",
        GMS_OPENAI_BASE_URL="https://gms.example.test/v1",
        AI_RECOMMENDATION_MODEL="gms-test-model",
    )
    def test_gms_missing_key_falls_back_to_rule_based(self):
        self.client.force_authenticate(self.user)

        response = self.client.get("/api/v1/home/")

        self.assertEqual(response.status_code, 200)
        personal = response.data["personal_recommendations"]
        self.assertTrue(personal["available"])
        self.assertTrue(personal["fallback_used"])
        self.assertEqual(personal["provider"], "rule_based")
        self.assertEqual(personal["mode"], "fallback")

    @override_settings(
        AI_RECOMMENDATION_ENABLED=True,
        AI_RECOMMENDATION_PROVIDER="gms_chat",
        AI_RECOMMENDATION_FALLBACK_PROVIDER="rule_based",
        GMS_API_KEY="test-key",
        GMS_OPENAI_BASE_URL="https://gms.example.test/v1",
        AI_RECOMMENDATION_MODEL="gms-test-model",
    )
    def test_gms_malformed_json_falls_back_to_rule_based(self):
        self.client.force_authenticate(self.user)

        with patch(
            "apps.recommendations.providers.request_chat_json",
            side_effect=GMSClientError("malformed json"),
        ):
            response = self.client.get("/api/v1/home/")

        self.assertEqual(response.status_code, 200)
        personal = response.data["personal_recommendations"]
        self.assertTrue(personal["available"])
        self.assertTrue(personal["fallback_used"])
        self.assertEqual(personal["provider"], "rule_based")
        self.assertEqual(personal["mode"], "fallback")

    @override_settings(
        AI_RECOMMENDATION_ENABLED=True,
        AI_RECOMMENDATION_PROVIDER="gms_chat",
        AI_RECOMMENDATION_FALLBACK_PROVIDER="rule_based",
        GMS_API_KEY="test-key",
        GMS_OPENAI_BASE_URL="https://gms.example.test/v1",
        AI_RECOMMENDATION_MODEL="gms-test-model",
    )
    def test_gms_invalid_library_id_is_removed(self):
        self.client.force_authenticate(self.user)
        plan = {
            "priority_tags": [{"code": "facility_lounge", "weight": 1}],
            "priority_purposes": [],
            "preferred_regions": [],
            "weights": {},
        }
        rerank = {
            "items": [
                {
                    "library_id": 999999,
                    "rank": 1,
                    "confidence": 1,
                    "matched_priority_tags": ["facility_lounge"],
                    "evidence_codes": ["tag:facility_lounge"],
                    "recommendation_reason": "없는 도서관 추천",
                },
                {
                    "library_id": self.library.id,
                    "rank": 2,
                    "confidence": 0.82,
                    "matched_priority_tags": ["facility_lounge"],
                    "evidence_codes": ["tag:facility_lounge"],
                    "recommendation_reason": "휴게공간 선호가 반영된 추천이에요.",
                },
            ]
        }

        with patch("apps.recommendations.providers.request_chat_json", side_effect=[plan, rerank]):
            response = self.client.get("/api/v1/home/")

        personal = response.data["personal_recommendations"]
        self.assertTrue(personal["available"])
        self.assertFalse(personal["fallback_used"])
        self.assertEqual(personal["provider"], "gms_chat")
        self.assertEqual(len(personal["items"]), 1)
        self.assertEqual(personal["items"][0]["id"], self.library.id)

    @override_settings(
        AI_RECOMMENDATION_ENABLED=True,
        AI_RECOMMENDATION_PROVIDER="gms_chat",
        AI_RECOMMENDATION_FALLBACK_PROVIDER="rule_based",
        GMS_API_KEY="test-key",
        GMS_OPENAI_BASE_URL="https://gms.example.test/v1",
        AI_RECOMMENDATION_MODEL="gms-test-model",
    )
    def test_gms_invalid_tag_and_evidence_are_sanitized(self):
        self.client.force_authenticate(self.user)
        plan = {
            "priority_tags": [{"code": "facility_lounge", "weight": 1}, {"code": "missing_tag", "weight": 1}],
            "priority_purposes": [],
            "preferred_regions": [],
            "weights": {},
        }
        rerank = {
            "items": [
                {
                    "library_id": self.library.id,
                    "rank": 1,
                    "confidence": 0.91,
                    "matched_priority_tags": ["facility_lounge", "missing_tag"],
                    "evidence_codes": ["metric:made_up"],
                    "recommendation_reason": "없는 근거로 만든 추천 문장입니다.",
                }
            ]
        }

        with patch("apps.recommendations.providers.request_chat_json", side_effect=[plan, rerank]):
            response = self.client.get("/api/v1/home/")

        item = response.data["personal_recommendations"]["items"][0]
        self.assertEqual(item["matched_priority_tags"], [{"code": "facility_lounge", "label": "휴게공간"}])
        self.assertNotEqual(item["recommendation_reason"], "없는 근거로 만든 추천 문장입니다.")
        self.assertIn("휴게공간", item["recommendation_reason"])

    @override_settings(
        AI_RECOMMENDATION_ENABLED=True,
        AI_RECOMMENDATION_PROVIDER="gms_chat",
        AI_RECOMMENDATION_FALLBACK_PROVIDER="rule_based",
        GMS_API_KEY="test-key",
        GMS_OPENAI_BASE_URL="https://gms.example.test/v1",
        AI_RECOMMENDATION_MODEL="gms-test-model",
    )
    def test_gms_valid_json_applies_ai_fields_and_evidence_codes(self):
        plan = {
            "priority_tags": [{"code": "facility_lounge", "weight": 1}],
            "priority_purposes": [],
            "preferred_regions": [],
            "weights": {},
        }
        rerank = {
            "items": [
                {
                    "library_id": self.library.id,
                    "rank": 1,
                    "confidence": 0.88,
                    "matched_priority_tags": ["facility_lounge"],
                    "evidence_codes": ["tag:facility_lounge"],
                    "recommendation_reason": "휴게공간 선호가 반영된 추천이에요.",
                }
            ]
        }
        libraries = list(get_candidate_libraries())

        with patch("apps.recommendations.providers.request_chat_json", side_effect=[plan, rerank]):
            result = build_personal_recommendations_v4(
                libraries,
                build_stat_max(libraries),
                [],
                set(),
                ["facility_lounge"],
                {},
                {
                    "user_summary": {"signal_count": 0, "top_behavior_tags": []},
                    "manual_preferences": {
                        "purposes": [],
                        "regions": [],
                        "tags": ["facility_lounge"],
                    },
                    "available_tag_codes": ["facility_lounge"],
                },
                "선호 설정을 바탕으로 골랐어요.",
            )

        self.assertFalse(result["fallback_used"])
        self.assertEqual(result["provider"], "gms_chat")
        self.assertEqual(result["priority_tags"], [{"code": "facility_lounge", "label": "휴게공간", "weight": 1.0}])
        item = result["items"][0]
        self.assertEqual(item.ai_rank, 1)
        self.assertEqual(item.ai_confidence, 0.88)
        self.assertEqual(item.evidence_codes, ["tag:facility_lounge"])
        self.assertEqual(item.recommendation_reason, "휴게공간 선호가 반영된 추천이에요.")

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
