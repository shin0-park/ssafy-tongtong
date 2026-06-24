import json
import re
from urllib import error, request

from django.conf import settings


MAX_SUMMARY_LENGTH = 100


def enhance_summary_sentence(payload):
    if not is_summary_enabled():
        return None

    try:
        content = request_summary_sentence(payload)
    except (OSError, ValueError, KeyError, TypeError, error.URLError, error.HTTPError):
        return None

    content = normalize_sentence(content)
    if not is_valid_summary(content):
        return None
    return content


def is_summary_enabled():
    return (
        bool(getattr(settings, "GMS_SUMMARY_ENABLED", False))
        and bool(getattr(settings, "GMS_API_KEY", ""))
        and bool(getattr(settings, "GMS_OPENAI_BASE_URL", ""))
        and bool(getattr(settings, "GMS_MODEL", ""))
    )


def request_summary_sentence(payload):
    base_url = settings.GMS_OPENAI_BASE_URL.rstrip("/")
    request_body = {
        "model": settings.GMS_MODEL,
        "messages": [
            {
                "role": "system",
                "content": (
                    "너는 도서관 서비스의 사용자 성향 요약 문장을 다듬는다. "
                    "입력된 규칙 기반 문장의 사실만 유지하고, 새로운 도서관명, 책명, "
                    "프로그램명, 시설 정보는 만들지 않는다. 한국어 한 문장으로 80자 내외로 답한다."
                ),
            },
            {
                "role": "user",
                "content": json.dumps(build_safe_payload(payload), ensure_ascii=False),
            },
        ],
        "temperature": 0.2,
        "max_tokens": 120,
    }
    http_request = request.Request(
        f"{base_url}/chat/completions",
        data=json.dumps(request_body).encode("utf-8"),
        headers={
            "Authorization": f"Bearer {settings.GMS_API_KEY}",
            "Content-Type": "application/json",
        },
        method="POST",
    )
    with request.urlopen(http_request, timeout=settings.GMS_TIMEOUT_SECONDS) as response:
        response_body = json.loads(response.read().decode("utf-8"))
    return response_body["choices"][0]["message"]["content"]


def build_safe_payload(payload):
    return {
        "top_axis": payload.get("top_axis", ""),
        "top_labels": list(payload.get("top_labels", []))[:5],
        "signal_count": int(payload.get("signal_count") or 0),
        "rule_sentence": payload.get("rule_sentence", ""),
    }


def normalize_sentence(content):
    if content is None:
        return ""
    return " ".join(str(content).strip().strip('"').strip("'").split())


def is_valid_summary(content):
    if not content:
        return False
    if len(content) > MAX_SUMMARY_LENGTH:
        return False
    if "\n" in content or "\r" in content:
        return False
    sentence_marks = list(re.finditer(r"[.!?。！？]", content))
    if len(sentence_marks) > 1:
        return False
    if sentence_marks and sentence_marks[0].end() != len(content):
        return False
    return True
