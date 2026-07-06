import json
from datetime import time

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
    LibraryStatisticSnapshot,
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
    retrieve_personal_candidates,
    score_preferred_tag,
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

    def test_review_quiet_study_bridge_creates_reading_room_candidate_without_librarytag(self):
        review_tag = self.create_review_tag("review_quiet_study", "조용한 공부 환경")
        library = self.create_open_library("조용한열람도서관", "부산진구")
        LibraryFacilityProfile.objects.create(library=library, has_reading_room=True)
        self.create_statistic(library, reading_seat_count=200)

        before_count = LibraryTag.objects.count()
        candidates = self.retrieve_candidates_for_review_tags(["review_quiet_study"])

        self.assertGreater(len(candidates), 0)
        self.assertEqual(LibraryTag.objects.filter(tag=review_tag).count(), 0)
        self.assertEqual(LibraryTag.objects.count(), before_count)
        self.assertIn(library.id, [candidate["library_id"] for candidate in candidates])

    def test_review_comfortable_space_bridge_creates_lounge_candidate(self):
        self.create_review_tag("review_comfortable_space", "편안한 공간")
        library = self.create_open_library("편안한공간도서관", "수영구")
        LibraryFacilityProfile.objects.create(
            library=library,
            has_lounge=True,
            has_cafe=True,
            has_outdoor_space=True,
        )
        self.create_statistic(library, building_area=1200, site_area=1600)

        candidates = self.retrieve_candidates_for_review_tags(["review_comfortable_space"])

        self.assertGreater(len(candidates), 0)
        self.assertIn(library.id, [candidate["library_id"] for candidate in candidates])

    def test_review_only_behavior_tags_can_create_candidates_without_review_librarytag(self):
        for code in (
            "review_easy_to_visit",
            "review_kind_guidance",
            "review_quiet_study",
            "review_seats_sufficient",
            "review_comfortable_space",
        ):
            self.create_review_tag(code, code)
        library = self.create_open_library("리뷰성향후보도서관", "동래구")
        library.latitude = "35.2000000"
        library.longitude = "129.0800000"
        library.save(update_fields=["latitude", "longitude", "updated_at"])
        LibraryFacilityProfile.objects.create(
            library=library,
            has_reading_room=True,
            has_lounge=True,
            has_accessible_facility=True,
            has_elevator=True,
        )
        self.create_statistic(library, reading_seat_count=150, building_area=900)

        candidates = self.retrieve_candidates_for_review_tags(
            [
                "review_easy_to_visit",
                "review_kind_guidance",
                "review_quiet_study",
                "review_seats_sufficient",
                "review_comfortable_space",
            ]
        )

        self.assertGreater(len(candidates), 0)
        self.assertIn(library.id, [candidate["library_id"] for candidate in candidates])
        self.assertFalse(
            LibraryTag.objects.filter(
                tag__code__in=[
                    "review_easy_to_visit",
                    "review_kind_guidance",
                    "review_quiet_study",
                    "review_seats_sufficient",
                    "review_comfortable_space",
                ]
            ).exists()
        )

    def test_review_kind_guidance_does_not_create_direct_feature_score(self):
        self.create_review_tag("review_kind_guidance", "친절한 안내")
        library = self.create_open_library("친절점수없음도서관", "남구")
        LibraryFacilityProfile.objects.create(
            library=library,
            has_lounge=True,
            has_reading_room=True,
            has_accessible_facility=True,
        )
        stat_max = build_stat_max([library])

        self.assertEqual(score_preferred_tag(library, "review_kind_guidance", stat_max), 0)

    def test_late_open_bridge_scores_only_late_open_daily_schedule(self):
        late_library = self.create_open_library("늦게닫는도서관", "북구")
        normal_library = self.create_open_library("여섯시닫는도서관", "북구")
        unknown_library = self.create_open_library("운영미상도서관", "북구")

        late_schedule = LibraryDailySchedule.objects.get(library=late_library, date=timezone.localdate())
        late_schedule.close_time = time(20, 0)
        late_schedule.save(update_fields=["close_time", "updated_at"])

        unknown_schedule = LibraryDailySchedule.objects.get(library=unknown_library, date=timezone.localdate())
        unknown_schedule.status = ScheduleStatus.UNKNOWN
        unknown_schedule.open_time = None
        unknown_schedule.close_time = None
        unknown_schedule.save(update_fields=["status", "open_time", "close_time", "updated_at"])

        stat_max = build_stat_max([late_library, normal_library, unknown_library])

        self.assertGreater(score_preferred_tag(late_library, "late_open", stat_max), 0)
        self.assertEqual(score_preferred_tag(normal_library, "late_open", stat_max), 0)
        self.assertEqual(score_preferred_tag(unknown_library, "late_open", stat_max), 0)

    def test_late_open_bridge_scores_closes_next_day(self):
        library = self.create_open_library("다음날닫는도서관", "동구")
        schedule = LibraryDailySchedule.objects.get(library=library, date=timezone.localdate())
        schedule.close_time = time(1, 0)
        schedule.closes_next_day = True
        schedule.save(update_fields=["close_time", "closes_next_day", "updated_at"])

        self.assertGreater(score_preferred_tag(library, "late_open", build_stat_max([library])), 0)

    def test_review_parking_convenient_bridge_uses_parking_feature_only(self):
        review_tag = self.create_review_tag("review_parking_convenient", "주차 편의")
        parking_library = self.create_open_library("주차정보도서관", "강서구")
        no_parking_library = self.create_open_library("주차정보없음도서관", "강서구")
        LibraryFacilityProfile.objects.create(library=parking_library, has_parking=True)
        LibraryFacilityProfile.objects.create(library=no_parking_library, has_parking=False)
        stat_max = build_stat_max([parking_library, no_parking_library])
        before_count = LibraryTag.objects.count()

        self.assertGreater(score_preferred_tag(parking_library, "review_parking_convenient", stat_max), 0)
        self.assertEqual(score_preferred_tag(no_parking_library, "review_parking_convenient", stat_max), 0)
        self.assertEqual(LibraryTag.objects.filter(tag=review_tag).count(), 0)
        self.assertEqual(LibraryTag.objects.count(), before_count)

    def test_review_wifi_reliable_bridge_uses_wifi_and_digital_room_features(self):
        self.create_review_tag("review_wifi_reliable", "와이파이 안정")
        wifi_library = self.create_open_library("와이파이정보도서관", "해운대구")
        digital_library = self.create_open_library("디지털실정보도서관", "해운대구")
        no_feature_library = self.create_open_library("네트워크정보없음도서관", "해운대구")
        LibraryFacilityProfile.objects.create(library=wifi_library, has_wifi=True)
        LibraryFacilityProfile.objects.create(library=digital_library, has_digital_room=True)
        LibraryFacilityProfile.objects.create(library=no_feature_library, has_wifi=False, has_digital_room=False)
        stat_max = build_stat_max([wifi_library, digital_library, no_feature_library])

        self.assertGreater(score_preferred_tag(wifi_library, "review_wifi_reliable", stat_max), 0)
        self.assertGreater(score_preferred_tag(digital_library, "review_wifi_reliable", stat_max), 0)
        self.assertEqual(score_preferred_tag(no_feature_library, "review_wifi_reliable", stat_max), 0)

    def test_review_children_room_good_bridge_uses_children_room_or_library_type(self):
        self.create_review_tag("review_children_room_good", "어린이자료실 체감")
        room_library = self.create_open_library("어린이실정보도서관", "사하구")
        children_library = self.create_open_library("어린이유형도서관", "사하구")
        no_feature_library = self.create_open_library("어린이정보없음도서관", "사하구")
        children_library.library_type = LibraryType.CHILDREN
        children_library.save(update_fields=["library_type", "updated_at"])
        LibraryFacilityProfile.objects.create(library=room_library, has_children_room=True)
        LibraryFacilityProfile.objects.create(library=no_feature_library, has_children_room=False)
        stat_max = build_stat_max([room_library, children_library, no_feature_library])

        self.assertGreater(score_preferred_tag(room_library, "review_children_room_good", stat_max), 0)
        self.assertGreater(score_preferred_tag(children_library, "review_children_room_good", stat_max), 0)
        self.assertEqual(score_preferred_tag(no_feature_library, "review_children_room_good", stat_max), 0)

    def test_review_laptop_friendly_bridge_uses_digital_wifi_reading_room_and_seats(self):
        self.create_review_tag("review_laptop_friendly", "노트북 이용 체감")
        feature_library = self.create_open_library("노트북조건도서관", "연제구")
        no_feature_library = self.create_open_library("노트북조건없음도서관", "연제구")
        LibraryFacilityProfile.objects.create(
            library=feature_library,
            has_digital_room=True,
            has_wifi=True,
            has_reading_room=True,
        )
        LibraryFacilityProfile.objects.create(
            library=no_feature_library,
            has_digital_room=False,
            has_wifi=False,
            has_reading_room=False,
        )
        self.create_statistic(feature_library, reading_seat_count=120)
        self.create_statistic(no_feature_library, reading_seat_count=0)
        stat_max = build_stat_max([feature_library, no_feature_library])

        self.assertGreater(score_preferred_tag(feature_library, "review_laptop_friendly", stat_max), 0)
        self.assertEqual(score_preferred_tag(no_feature_library, "review_laptop_friendly", stat_max), 0)

    def test_review_stay_friendly_bridge_uses_space_and_seat_features(self):
        self.create_review_tag("review_stay_friendly", "오래 머물기 체감")
        feature_library = self.create_open_library("체류조건도서관", "수영구")
        no_feature_library = self.create_open_library("체류조건없음도서관", "수영구")
        LibraryFacilityProfile.objects.create(
            library=feature_library,
            has_lounge=True,
            has_cafe=True,
            has_outdoor_space=True,
        )
        LibraryFacilityProfile.objects.create(
            library=no_feature_library,
            has_lounge=False,
            has_cafe=False,
            has_outdoor_space=False,
        )
        self.create_statistic(feature_library, reading_seat_count=80, building_area=1200, site_area=1600)
        self.create_statistic(no_feature_library, reading_seat_count=0, building_area=0, site_area=0)
        stat_max = build_stat_max([feature_library, no_feature_library])

        self.assertGreater(score_preferred_tag(feature_library, "review_stay_friendly", stat_max), 0)
        self.assertEqual(score_preferred_tag(no_feature_library, "review_stay_friendly", stat_max), 0)

    @override_settings(
        AI_RECOMMENDATION_ENABLED=True,
        AI_RECOMMENDATION_PROVIDER="mock",
        AI_RECOMMENDATION_FALLBACK_PROVIDER="rule_based",
    )
    def test_primary_failure_logs_provider_stage_and_error(self):
        class BrokenPrimaryProvider:
            provider_code = "broken_primary"

            def plan_preferences(self, context):
                raise RecommendationProviderError("planner exploded")

            def rerank_libraries(self, bundle):
                return {"items": []}

        self.client.force_authenticate(self.user)
        with patch(
            "apps.recommendations.services.get_provider",
            side_effect=[BrokenPrimaryProvider(), RuleBasedFallbackRecommendationProvider()],
        ):
            with self.assertLogs("apps.recommendations.services", level="WARNING") as logs:
                response = self.client.get("/api/v1/home/")

        self.assertEqual(response.status_code, 200)
        self.assertTrue(response.data["personal_recommendations"]["fallback_used"])
        self.assertTrue(any("provider=mock" in message for message in logs.output))
        self.assertTrue(any("stage=planner_call" in message for message in logs.output))
        self.assertTrue(any("error=RecommendationProviderError" in message for message in logs.output))

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
            with self.assertLogs("apps.recommendations.services", level="WARNING") as logs:
                response = self.client.get("/api/v1/home/")

        self.assertEqual(response.status_code, 200)
        personal = response.data["personal_recommendations"]
        self.assertFalse(personal["available"])
        self.assertEqual(personal["items"], [])
        self.assertEqual(personal["priority_tags"], [])
        self.assertTrue(personal["fallback_used"])
        self.assertEqual(personal["provider"], "rule_based")
        self.assertEqual(personal["mode"], "fallback_failed")
        self.assertTrue(any("stage=provider_get" in message for message in logs.output))
        self.assertTrue(any("stage=fallback_planner" in message for message in logs.output))

    def create_review_tag(self, code, label):
        return Tag.objects.create(
            code=code,
            label=label,
            semantic_kind=TagSemanticKind.EXPERIENCE,
            tag_group=TagGroup.STUDY_READING,
            is_profile_selectable=False,
            is_review_selectable=False,
        )

    def create_statistic(
        self,
        library,
        *,
        reading_seat_count=0,
        book_count=0,
        building_area=0,
        site_area=0,
    ):
        return LibraryStatisticSnapshot.objects.create(
            library=library,
            provider_code="test",
            reference_date=timezone.localdate(),
            reading_seat_count=reading_seat_count,
            book_count=book_count,
            building_area=building_area,
            site_area=site_area,
            is_current=True,
        )

    def retrieve_candidates_for_review_tags(self, tag_codes):
        libraries = list(get_candidate_libraries())
        plan = {
            "priority_tags": [{"code": code, "weight": 0.7} for code in tag_codes],
            "preferred_regions": [],
        }
        candidates, _ = retrieve_personal_candidates(
            libraries,
            build_stat_max(libraries),
            [],
            set(),
            [],
            {},
            plan,
            "저장과 후기 활동을 바탕으로 골랐어요.",
        )
        return candidates

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
