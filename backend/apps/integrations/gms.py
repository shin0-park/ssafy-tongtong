import json
import re
from urllib import error, request

from django.conf import settings


MAX_SUMMARY_LENGTH = 100


class GMSClientError(RuntimeError):
    pass


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


def request_chat_json(messages, *, model, timeout_seconds, max_tokens=800):
    if not getattr(settings, "GMS_API_KEY", ""):
        raise GMSClientError("GMS_API_KEY is not configured.")
    if not getattr(settings, "GMS_OPENAI_BASE_URL", ""):
        raise GMSClientError("GMS_OPENAI_BASE_URL is not configured.")
    if not model:
        raise GMSClientError("GMS model is not configured.")

    base_url = settings.GMS_OPENAI_BASE_URL.rstrip("/")
    request_body = {
        "model": model,
        "messages": messages,
        "max_completion_tokens": max_tokens,
        "response_format": {"type": "json_object"},
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
    try:
        with request.urlopen(http_request, timeout=timeout_seconds) as response:
            response_body = json.loads(response.read().decode("utf-8"))
        content = response_body["choices"][0]["message"]["content"]
        if not content:
            raise GMSClientError("chat completion content was empty")
        parsed = json.loads(content)
    except error.HTTPError as exc:
        raise GMSClientError(format_http_error(exc)) from exc
    except GMSClientError:
        raise
    except (json.JSONDecodeError, ValueError, KeyError, TypeError) as exc:
        raise GMSClientError("JSON parse failed: response content was not a JSON object") from exc
    except (OSError, error.URLError) as exc:
        raise GMSClientError(f"GMS chat request failed: {exc.__class__.__name__}") from exc

    if not isinstance(parsed, dict):
        raise GMSClientError("JSON parse failed: response content was not a JSON object")
    return parsed


def format_http_error(exc):
    provider_message = extract_provider_error_message(exc)
    if provider_message:
        return f"HTTPError {exc.code}: {provider_message}"
    return f"HTTPError {exc.code}: {exc.reason}"


def extract_provider_error_message(exc):
    try:
        body = exc.read().decode("utf-8", errors="replace")
    except (OSError, UnicodeDecodeError):
        return ""
    if not body:
        return ""
    try:
        payload = json.loads(body)
    except json.JSONDecodeError:
        return ""

    error_payload = payload.get("error") if isinstance(payload, dict) else None
    if isinstance(error_payload, dict):
        message = error_payload.get("message")
        if isinstance(message, str):
            return message[:300]
    return ""


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
