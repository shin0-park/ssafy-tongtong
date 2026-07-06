import json
from typing import Protocol

from django.conf import settings

from apps.integrations.gms import GMSClientError, request_chat_json


class RecommendationProviderError(RuntimeError):
    pass


class RecommendationProvider(Protocol):
    provider_code: str

    def plan_preferences(self, context):
        ...

    def rerank_libraries(self, bundle):
        ...


class MockRecommendationProvider:
    provider_code = "mock"

    def plan_preferences(self, context):
        return build_rule_based_plan(context)

    def rerank_libraries(self, bundle):
        items = []
        priority_tag_codes = {
            item["code"] for item in bundle.get("plan", {}).get("priority_tags", [])
        }
        for index, candidate in enumerate(bundle.get("candidates", []), start=1):
            feature_tags = candidate.get("feature_tags", [])
            matched_tags = [code for code in feature_tags if code in priority_tag_codes]
            evidence_codes = [f"tag:{code}" for code in matched_tags]
            if candidate.get("matched_region"):
                evidence_codes.append(f"region:{candidate.get('sigungu')}")
            if candidate.get("operation", {}).get("open_today") is True:
                evidence_codes.append("operation:open_today")
            items.append(
                {
                    "library_id": candidate["library_id"],
                    "rank": index,
                    "confidence": 0.75 if matched_tags else 0.55,
                    "matched_priority_tags": matched_tags[:3],
                    "evidence_codes": evidence_codes[:3],
                    "recommendation_reason": build_candidate_reason(candidate, matched_tags),
                }
            )
        return {"items": items}


class RuleBasedFallbackRecommendationProvider:
    provider_code = "rule_based"

    def plan_preferences(self, context):
        return build_rule_based_plan(context)

    def rerank_libraries(self, bundle):
        return {
            "items": [
                {
                    "library_id": candidate["library_id"],
                    "rank": index,
                    "confidence": 0.0,
                    "matched_priority_tags": candidate.get("feature_tags", [])[:3],
                    "evidence_codes": candidate.get("allowed_evidence_codes", [])[:3],
                    "recommendation_reason": candidate.get("fallback_reason") or "선호와 활동 기준으로 골랐어요.",
                }
                for index, candidate in enumerate(bundle.get("candidates", []), start=1)
            ]
        }


class GMSChatRecommendationProvider:
    provider_code = "gms_chat"

    def plan_preferences(self, context):
        return self.request_json(
            [
                {
                    "role": "system",
                    "content": (
                        "너는 도서관 나들이 서비스의 AI Preference Planner다. "
                        "사용자 행동 요약, 수동 선호, 사용 가능한 tag_code 목록만 보고 추천 검색 계획을 만든다. "
                        "전체 도서관 raw data는 입력받지 않으며, 도서관 사실을 만들거나 수정하지 않는다. "
                        "priority_purposes, priority_tags, preferred_regions, weights 키만 가진 JSON object를 반환한다. "
                        "priority_purposes와 priority_tags는 {code, weight} 배열이고, preferred_regions는 {sigungu, weight} 배열이다. "
                        "입력 available_tag_codes에 없는 tag_code를 절대 출력하지 않는다. "
                        "weights는 purpose, tag, region, distance 숫자 값을 포함한다. JSON 외 텍스트는 출력하지 않는다."
                    ),
                },
                {
                    "role": "user",
                    "content": json.dumps(
                        {
                            "user_summary": context.get("user_summary", {}),
                            "manual_preferences": context.get("manual_preferences", {}),
                            "available_tag_codes": context.get("available_tag_codes", []),
                        },
                        ensure_ascii=False,
                    ),
                },
            ],
            max_tokens=700,
        )

    def rerank_libraries(self, bundle):
        return self.request_json(
            [
                {
                    "role": "system",
                    "content": (
                        "너는 도서관 나들이 서비스의 AI Reranker다. "
                        "Django가 고른 후보 10~20개의 요약 feature만 보고 최종 순위를 정한다. "
                        "입력에 있는 library_id, tag_code, allowed_evidence_codes만 사용한다. "
                        "없는 시설, 운영 여부, 장서, 위치, 후기, 이미지 사실을 만들지 않는다. "
                        "recommendation_reason은 evidence_codes에 포함한 근거에 기반해서만 짧은 한국어 한 문장으로 작성한다. "
                        "출력은 {items: [...]} JSON object 하나만 반환한다. "
                        "각 item은 library_id, rank, confidence, matched_priority_tags, evidence_codes, recommendation_reason을 포함한다. "
                        "matched_priority_tags는 입력 plan.priority_tags의 code 중 후보 feature_tags에 있는 값만 사용한다. "
                        "evidence_codes는 해당 후보의 allowed_evidence_codes 안에 있는 값만 사용한다. JSON 외 텍스트는 출력하지 않는다."
                    ),
                },
                {
                    "role": "user",
                    "content": json.dumps(
                        {
                            "plan": bundle.get("plan", {}),
                            "candidates": bundle.get("candidates", []),
                        },
                        ensure_ascii=False,
                    ),
                },
            ],
            max_tokens=1200,
        )

    def request_json(self, messages, *, max_tokens):
        model = getattr(settings, "AI_RECOMMENDATION_MODEL", "") or getattr(settings, "GMS_MODEL", "")
        timeout_seconds = getattr(settings, "AI_RECOMMENDATION_TIMEOUT_SECONDS", 5)
        try:
            return request_chat_json(
                messages,
                model=model,
                timeout_seconds=timeout_seconds,
                max_tokens=max_tokens,
            )
        except GMSClientError as exc:
            raise RecommendationProviderError(str(exc)) from exc


class FineTunedRecommendationProvider:
    provider_code = "fine_tuned"

    def plan_preferences(self, context):
        raise RecommendationProviderError("Fine-tuned recommendation provider is not implemented in phase 1.")

    def rerank_libraries(self, bundle):
        raise RecommendationProviderError("Fine-tuned recommendation provider is not implemented in phase 1.")


def get_provider(provider_code):
    providers = {
        "mock": MockRecommendationProvider,
        "rule_based": RuleBasedFallbackRecommendationProvider,
        "gms_chat": GMSChatRecommendationProvider,
        "fine_tuned": FineTunedRecommendationProvider,
    }
    provider_class = providers.get(provider_code)
    if provider_class is None:
        raise RecommendationProviderError(f"Unknown recommendation provider: {provider_code}")
    return provider_class()


def build_rule_based_plan(context):
    manual = context.get("manual_preferences", {})
    behavior_tags = context.get("user_summary", {}).get("top_behavior_tags", [])
    priority_tags = []
    seen_tag_codes = set()

    for tag_code in manual.get("tags", []):
        if tag_code and tag_code not in seen_tag_codes:
            priority_tags.append({"code": tag_code, "weight": 1.0})
            seen_tag_codes.add(tag_code)
    for item in behavior_tags:
        tag_code = item.get("code")
        if tag_code and tag_code not in seen_tag_codes:
            priority_tags.append({"code": tag_code, "weight": 0.7})
            seen_tag_codes.add(tag_code)

    return {
        "priority_purposes": [
            {"code": code, "weight": 1.0}
            for code in manual.get("purposes", [])
            if code
        ],
        "priority_tags": priority_tags[:5],
        "preferred_regions": [
            {"sigungu": sigungu, "weight": 1.0}
            for sigungu in manual.get("regions", [])
            if sigungu
        ],
        "weights": {
            "purpose": 0.3,
            "tag": 0.4,
            "region": 0.2,
            "distance": 0.1,
        },
    }


def build_candidate_reason(candidate, matched_tags):
    if matched_tags:
        return "우선 태그와 도서관 특성이 잘 맞아 추천했어요."
    if candidate.get("matched_region"):
        return "선호 지역과 활동 기준을 함께 반영했어요."
    return candidate.get("fallback_reason") or "선호와 활동 기준으로 골랐어요."
