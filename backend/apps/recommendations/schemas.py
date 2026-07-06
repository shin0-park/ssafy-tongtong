class RecommendationSchemaError(ValueError):
    pass


DEFAULT_WEIGHTS = {
    "purpose": 0.3,
    "tag": 0.4,
    "region": 0.2,
    "distance": 0.1,
}


def validate_preference_plan(raw_plan, *, valid_purpose_codes, valid_tag_codes):
    if not isinstance(raw_plan, dict):
        raise RecommendationSchemaError("Planner output must be an object.")

    valid_purpose_codes = set(valid_purpose_codes)
    valid_tag_codes = set(valid_tag_codes)

    return {
        "priority_purposes": validate_weighted_code_items(
            raw_plan.get("priority_purposes", []),
            valid_codes=valid_purpose_codes,
            code_key="code",
        ),
        "priority_tags": validate_weighted_code_items(
            raw_plan.get("priority_tags", []),
            valid_codes=valid_tag_codes,
            code_key="code",
        ),
        "preferred_regions": validate_weighted_regions(raw_plan.get("preferred_regions", [])),
        "weights": validate_weights(raw_plan.get("weights", {})),
    }


def validate_rerank_result(raw_result, *, candidate_by_id, valid_tag_codes):
    if not isinstance(raw_result, dict):
        raise RecommendationSchemaError("Reranker output must be an object.")
    raw_items = raw_result.get("items")
    if not isinstance(raw_items, list):
        raise RecommendationSchemaError("Reranker output items must be a list.")

    valid_tag_codes = set(valid_tag_codes)
    seen_library_ids = set()
    items = []
    for raw_item in raw_items:
        if not isinstance(raw_item, dict):
            continue
        library_id = parse_positive_int(raw_item.get("library_id"))
        if not library_id or library_id in seen_library_ids or library_id not in candidate_by_id:
            continue
        candidate = candidate_by_id[library_id]["public"]
        rank = parse_positive_int(raw_item.get("rank")) or len(items) + 1
        confidence = clamp_float(raw_item.get("confidence"), default=0.0)
        matched_priority_tags = [
            code
            for code in raw_item.get("matched_priority_tags", [])
            if isinstance(code, str) and code in valid_tag_codes
        ]
        reason = normalize_reason(raw_item.get("recommendation_reason"))
        evidence_codes = validate_evidence_codes(
            raw_item.get("evidence_codes", []),
            allowed_evidence_codes=candidate.get("allowed_evidence_codes", []),
        )
        if not reason or not evidence_codes:
            reason = build_fallback_reason(candidate, matched_priority_tags, evidence_codes)
        items.append(
            {
                "library_id": library_id,
                "rank": rank,
                "confidence": confidence,
                "matched_priority_tags": matched_priority_tags,
                "evidence_codes": evidence_codes,
                "recommendation_reason": reason,
            }
        )
        seen_library_ids.add(library_id)

    items.sort(key=lambda item: (item["rank"], item["library_id"]))
    for index, item in enumerate(items, start=1):
        item["rank"] = index
    return {"items": items}


def validate_weighted_code_items(raw_items, *, valid_codes, code_key):
    if raw_items in (None, ""):
        return []
    if not isinstance(raw_items, list):
        raise RecommendationSchemaError(f"{code_key} items must be a list.")

    items = []
    seen_codes = set()
    for raw_item in raw_items:
        if not isinstance(raw_item, dict):
            continue
        code = raw_item.get(code_key)
        if not isinstance(code, str) or code not in valid_codes or code in seen_codes:
            continue
        items.append({"code": code, "weight": clamp_float(raw_item.get("weight"), default=1.0)})
        seen_codes.add(code)
    return items


def validate_evidence_codes(raw_items, *, allowed_evidence_codes):
    if not isinstance(raw_items, list):
        return []

    allowed_evidence_codes = set(allowed_evidence_codes or [])
    evidence_codes = []
    seen_codes = set()
    for code in raw_items:
        if not isinstance(code, str) or code not in allowed_evidence_codes or code in seen_codes:
            continue
        evidence_codes.append(code)
        seen_codes.add(code)
    return evidence_codes


def build_fallback_reason(candidate, matched_priority_tags, evidence_codes):
    allowed_evidence_codes = set(candidate.get("allowed_evidence_codes", []))
    labels = candidate.get("evidence_labels", {})
    reason_parts = []

    for tag_code in matched_priority_tags:
        evidence_code = f"tag:{tag_code}"
        if evidence_code in allowed_evidence_codes:
            reason_parts.append(labels.get(evidence_code, "관심 태그"))

    for evidence_code in evidence_codes:
        if evidence_code in allowed_evidence_codes:
            reason_parts.append(labels.get(evidence_code, "추천 근거"))

    if not reason_parts and "operation:open_today" in allowed_evidence_codes:
        reason_parts.append(labels.get("operation:open_today", "오늘 운영"))
    if not reason_parts and candidate.get("matched_region"):
        region_code = f"region:{candidate.get('sigungu')}"
        if region_code in allowed_evidence_codes:
            reason_parts.append(labels.get(region_code, "선호 지역"))

    reason_parts = dedupe(reason_parts)[:2]
    if not reason_parts:
        return candidate.get("fallback_reason") or "선호와 활동 기준으로 골랐어요."
    if len(reason_parts) == 1:
        return f"{reason_parts[0]} 기준이 반영된 추천이에요."
    return f"{reason_parts[0]}와 {reason_parts[1]} 기준이 함께 반영된 추천이에요."


def validate_weighted_regions(raw_items):
    if raw_items in (None, ""):
        return []
    if not isinstance(raw_items, list):
        raise RecommendationSchemaError("preferred_regions must be a list.")

    items = []
    seen_regions = set()
    for raw_item in raw_items:
        if not isinstance(raw_item, dict):
            continue
        sigungu = raw_item.get("sigungu")
        if not isinstance(sigungu, str):
            continue
        sigungu = sigungu.strip()
        if not sigungu or sigungu in seen_regions:
            continue
        items.append({"sigungu": sigungu, "weight": clamp_float(raw_item.get("weight"), default=1.0)})
        seen_regions.add(sigungu)
    return items


def validate_weights(raw_weights):
    if raw_weights in (None, ""):
        return dict(DEFAULT_WEIGHTS)
    if not isinstance(raw_weights, dict):
        raise RecommendationSchemaError("weights must be an object.")
    weights = {}
    for key, default in DEFAULT_WEIGHTS.items():
        weights[key] = clamp_float(raw_weights.get(key), default=default)
    return weights


def parse_positive_int(value):
    try:
        parsed = int(value)
    except (TypeError, ValueError):
        return None
    return parsed if parsed > 0 else None


def clamp_float(value, *, default):
    try:
        parsed = float(value)
    except (TypeError, ValueError):
        return default
    if parsed < 0:
        return 0.0
    if parsed > 1:
        return 1.0
    return parsed


def normalize_reason(value):
    if not isinstance(value, str):
        return ""
    return " ".join(value.strip().split())[:160]


def dedupe(values):
    deduped = []
    for value in values:
        if value and value not in deduped:
            deduped.append(value)
    return deduped
