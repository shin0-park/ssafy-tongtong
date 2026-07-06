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
        rank = parse_positive_int(raw_item.get("rank")) or len(items) + 1
        confidence = clamp_float(raw_item.get("confidence"), default=0.0)
        matched_priority_tags = [
            code
            for code in raw_item.get("matched_priority_tags", [])
            if isinstance(code, str) and code in valid_tag_codes
        ]
        reason = normalize_reason(raw_item.get("recommendation_reason"))
        items.append(
            {
                "library_id": library_id,
                "rank": rank,
                "confidence": confidence,
                "matched_priority_tags": matched_priority_tags,
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
