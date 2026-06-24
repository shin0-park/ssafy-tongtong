BUSAN_SIDO = "부산광역시"
BUSAN_REGION_CODE = "21"

BUSAN_SIGUNGU_LIST = (
    "강서구",
    "금정구",
    "기장군",
    "남구",
    "동구",
    "동래구",
    "부산진구",
    "북구",
    "사상구",
    "사하구",
    "서구",
    "수영구",
    "연제구",
    "영도구",
    "중구",
    "해운대구",
)

BUSAN_SIGUNGU_SET = set(BUSAN_SIGUNGU_LIST)


def build_region_key(sigungu):
    return f"{BUSAN_REGION_CODE}:{sigungu}"


def get_busan_region_options():
    return [
        {
            "region_key": build_region_key(sigungu),
            "sido": BUSAN_SIDO,
            "sigungu": sigungu,
            "label": sigungu,
        }
        for sigungu in BUSAN_SIGUNGU_LIST
    ]
