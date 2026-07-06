from typing import Protocol


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
            items.append(
                {
                    "library_id": candidate["library_id"],
                    "rank": index,
                    "confidence": 0.75 if matched_tags else 0.55,
                    "matched_priority_tags": matched_tags[:3],
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
                    "recommendation_reason": candidate.get("fallback_reason") or "선호와 활동 기준으로 골랐어요.",
                }
                for index, candidate in enumerate(bundle.get("candidates", []), start=1)
            ]
        }


class GMSChatRecommendationProvider:
    provider_code = "gms_chat"

    def plan_preferences(self, context):
        raise RecommendationProviderError("GMS recommendation provider is not implemented in phase 1.")

    def rerank_libraries(self, bundle):
        raise RecommendationProviderError("GMS recommendation provider is not implemented in phase 1.")


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
