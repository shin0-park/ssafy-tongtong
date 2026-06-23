from django.core.management.base import BaseCommand
from django.db import transaction

from apps.recommendations.models import (
    DailyRecommendationMetricRule,
    DailyRecommendationTagRule,
    DailyRecommendationTheme,
    Purpose,
    PurposeMetricRule,
    PurposeTagRule,
)
from apps.tags.models import Tag


TAG_SEEDS = [
    ("public_library", "공공도서관", "classification", "library_type", "", True, False, "", "", True, 10, 0),
    ("small_library", "작은도서관", "classification", "library_type", "", True, False, "", "", True, 20, 0),
    ("children_library", "어린이도서관", "classification", "library_type", "", True, False, "", "", True, 30, 0),
    ("many_seats", "좌석이 많은 도서관", "objective", "study_reading", "", True, False, "", "", True, 110, 0),
    ("rich_collection", "장서가 많은 도서관", "objective", "collection", "", True, False, "", "", True, 120, 0),
    ("late_open", "늦게까지 운영", "objective", "operation", "", True, False, "", "", True, 130, 0),
    ("facility_reading_room", "열람실", "objective", "facility", "열람실 또는 일반 열람 공간이 확인된 도서관", True, False, "", "", True, 210, 0),
    ("facility_children_room", "어린이자료실", "objective", "facility", "어린이자료실 보유가 확인된 도서관", True, False, "", "", True, 220, 0),
    ("facility_digital_room", "디지털자료실", "objective", "facility", "", True, False, "", "", True, 230, 0),
    ("facility_parking", "주차장", "objective", "facility", "주차장 보유 여부", True, False, "", "", True, 240, 0),
    ("facility_cafe", "카페", "objective", "facility", "", True, False, "", "", True, 250, 0),
    ("facility_wifi", "무료 와이파이", "objective", "facility", "와이파이 제공 여부", True, False, "", "", True, 260, 0),
    ("facility_nursing_room", "수유실", "objective", "facility", "", True, False, "", "", True, 270, 0),
    ("facility_accessible", "이동약자 편의시설", "objective", "facility", "", True, False, "", "", True, 280, 0),
    ("facility_elevator", "엘리베이터", "objective", "facility", "", True, False, "", "", True, 290, 0),
    ("facility_lounge", "휴게 공간", "objective", "facility", "", True, False, "", "", True, 300, 0),
    ("facility_outdoor_space", "야외 공간", "objective", "facility", "", True, False, "", "", True, 310, 0),
    ("book_literature", "문학", "content", "book_subject", "", True, False, "", "", True, 410, 0),
    ("book_science", "과학", "content", "book_subject", "", True, False, "", "", True, 420, 0),
    ("book_social_science", "사회과학", "content", "book_subject", "", True, False, "", "", True, 430, 0),
    ("book_history", "역사", "content", "book_subject", "", True, False, "", "", True, 440, 0),
    ("book_art", "예술", "content", "book_subject", "", True, False, "", "", True, 450, 0),
    ("program_lecture_humanities", "인문 강좌", "classification", "program_type", "", True, False, "", "", True, 510, 0),
    ("program_reading_writing", "독서·글쓰기 프로그램", "classification", "program_type", "", True, False, "", "", True, 520, 0),
    ("program_culture_art", "문화·예술 프로그램", "classification", "program_type", "", True, False, "", "", True, 530, 0),
    ("program_experience_education", "체험·교육 프로그램", "classification", "program_type", "", True, False, "", "", True, 540, 0),
    ("program_exhibition", "전시 프로그램", "classification", "program_type", "", True, False, "", "", True, 550, 0),
    ("for_infant", "유아 대상", "classification", "program_target", "", True, False, "", "", True, 610, 0),
    ("for_elementary", "초등학생 대상", "classification", "program_target", "", True, False, "", "", True, 620, 0),
    ("for_teen", "청소년 대상", "classification", "program_target", "", True, False, "", "", True, 630, 0),
    ("for_adult", "성인 대상", "classification", "program_target", "", True, False, "", "", True, 640, 0),
    ("for_senior", "시니어 대상", "classification", "program_target", "", True, False, "", "", True, 650, 0),
    ("for_family", "가족 대상", "classification", "program_target", "", True, False, "", "", True, 660, 0),
    ("for_other", "기타 대상", "classification", "program_target", "", True, False, "", "", True, 670, 0),
    ("review_quiet_study", "조용한 공부 환경", "experience", "study_reading", "", False, True, "조용히 공부하기 좋아요", "study_reading", False, 1010, 10),
    ("review_focused_atmosphere", "집중하기 좋은 분위기", "experience", "study_reading", "", False, True, "집중하기 좋은 분위기예요", "study_reading", False, 1020, 20),
    ("review_seats_sufficient", "충분하다고 느낀 좌석", "experience", "study_reading", "", False, True, "앉을 자리가 충분해요", "study_reading", False, 1030, 30),
    ("review_comfortable_reading_space", "쾌적한 열람공간", "experience", "study_reading", "", False, True, "열람공간이 쾌적해요", "study_reading", False, 1040, 40),
    ("review_laptop_friendly", "노트북 이용 친화", "experience", "study_reading", "", False, True, "노트북 쓰기 좋아요", "study_reading", False, 1050, 50),
    ("review_comfortable_space", "편안한 공간", "experience", "space_atmosphere", "", False, True, "공간이 편안해요", "space_atmosphere", False, 1110, 10),
    ("review_clean_space", "깔끔하고 쾌적한 공간", "experience", "space_atmosphere", "", False, True, "깔끔하고 쾌적해요", "space_atmosphere", False, 1120, 20),
    ("review_stay_friendly", "오래 머물기 좋은 공간", "experience", "space_atmosphere", "", False, True, "오래 머물기 좋아요", "space_atmosphere", False, 1130, 30),
    ("review_good_nearby_scenery", "주변 경관", "experience", "space_atmosphere", "", False, True, "근처 경관이 좋아요", "space_atmosphere", False, 1140, 40),
    ("review_outdoor_space_good", "만족스러운 야외공간", "experience", "space_atmosphere", "", False, True, "야외공간이 좋아요", "space_atmosphere", False, 1150, 50),
    ("review_books_diverse", "다양하다고 느낀 장서", "experience", "collection", "", False, True, "책이 다양해요", "collection", False, 1210, 10),
    ("review_frequent_new_books", "신간 자료", "experience", "collection", "", False, True, "신간이 잘 들어와요", "collection", False, 1220, 20),
    ("review_good_children_books", "어린이책", "experience", "collection", "", False, True, "어린이책이 좋아요", "collection", False, 1230, 30),
    ("review_easy_book_finding", "책 찾기 편함", "experience", "collection", "", False, True, "책 찾기가 편해요", "collection", False, 1240, 40),
    ("review_good_programs", "만족도 높은 프로그램", "experience", "program_type", "", False, True, "프로그램이 좋아요", "program", False, 1310, 10),
    ("review_programs_diverse", "다양하다고 느낀 프로그램", "experience", "program_type", "", False, True, "프로그램이 다양해요", "program", False, 1320, 20),
    ("review_program_culture_art_good", "문화·예술 프로그램 만족", "experience", "program_type", "", False, True, "문화·예술 프로그램이 좋아요", "program", False, 1330, 30),
    ("review_program_reading_writing_good", "독서·글쓰기 프로그램 만족", "experience", "program_type", "", False, True, "독서·글쓰기 프로그램이 좋아요", "program", False, 1340, 40),
    ("review_children_friendly", "아이와 방문하기 좋음", "experience", "kids_family", "", False, True, "아이와 가기 좋아요", "kids_family", False, 1410, 10),
    ("review_children_room_good", "어린이자료실 만족", "experience", "kids_family", "", False, True, "어린이자료실이 좋아요", "kids_family", False, 1420, 20),
    ("review_family_friendly", "가족 친화", "experience", "kids_family", "", False, True, "가족이 함께 가기 좋아요", "kids_family", False, 1430, 30),
    ("review_good_children_programs", "어린이 프로그램", "experience", "kids_family", "", False, True, "어린이 프로그램이 좋아요", "kids_family", False, 1440, 40),
    ("review_easy_to_visit", "찾아가기 쉬움", "experience", "access_convenience", "", False, True, "찾아가기 쉬워요", "access_convenience", False, 1510, 10),
    ("review_parking_convenient", "주차 편의", "experience", "access_convenience", "", False, True, "주차가 편해요", "access_convenience", False, 1520, 20),
    ("review_public_transport_access", "대중교통 접근성", "experience", "access_convenience", "", False, True, "대중교통으로 가기 좋아요", "access_convenience", False, 1530, 30),
    ("review_wifi_reliable", "와이파이 사용 경험", "experience", "access_convenience", "", False, True, "와이파이가 잘 돼요", "access_convenience", False, 1540, 40),
    ("review_accessible_use_convenient", "이동약자 이용 편의", "experience", "access_convenience", "", False, True, "이동약자도 이용하기 좋아요", "access_convenience", False, 1550, 50),
    ("review_kind_guidance", "친절한 안내", "experience", "guidance_management", "", False, True, "안내가 친절해요", "guidance_management", False, 1610, 10),
    ("review_well_managed", "관리 상태 양호", "experience", "guidance_management", "", False, True, "관리가 잘 되어 있어요", "guidance_management", False, 1620, 20),
]


PURPOSE_SEEDS = [
    ("study", "공부하러 가고 싶어요", "차분히 앉아 공부하거나 작업하기 좋은 도서관", 10, True, True, "study", False),
    ("book", "책을 둘러보고 싶어요", "장서와 자료 탐색에 강점이 있는 도서관", 20, True, True, "book", False),
    ("kids", "아이와 함께 가고 싶어요", "어린이와 가족 방문에 어울리는 도서관", 30, True, True, "", False),
    ("mood", "분위기 좋은 곳에 가고 싶어요", "공간과 분위기를 함께 즐기기 좋은 도서관", 40, True, True, "rest", False),
    ("nearby", "가까운 곳에 가고 싶어요", "요청 좌표 기준으로 가까운 도서관", 50, True, True, "", True),
    ("program", "프로그램을 즐기고 싶어요", "문화 프로그램 탐색과 개인화 분석에 쓰는 목적", 60, False, True, "program", False),
]


DAILY_THEME_SEEDS = [
    ("large_space", "넓은 공간", "오늘은 조금 넓은 도서관으로 가볼까요?", "면적 지표와 선택적 공간 경험 태그를 반영합니다.", 10),
    ("rich_collection", "풍부한 장서", "서가 사이를 천천히 둘러보기 좋은 날이에요", "장서 수와 자료 다양성 경험 태그를 반영합니다.", 20),
    ("mood_space", "분위기 좋은 공간", "분위기도 함께 즐겨보세요", "야외 공간과 주변 경관 경험 태그를 반영합니다.", 30),
    ("study_seats", "공부 좌석", "오늘은 차분히 앉아 있을 곳을 찾아볼까요?", "열람 좌석과 공부 경험 태그를 반영합니다.", 40),
    ("family_outing", "가족 나들이", "가족 나들이처럼 들르기 좋은 도서관이에요", "어린이자료실과 가족 방문 경험 태그를 반영합니다.", 50),
    ("restful_space", "쉬어가기 좋은 공간", "잠깐 쉬어가도 좋은 공간을 골라봤어요", "휴게 공간과 머무름 경험 태그를 반영합니다.", 60),
]


PURPOSE_METRIC_RULES = [
    ("study", "reading_seat_count", "1.0000", False, {"method": "minmax", "direction": "higher"}),
    ("study", "late_close_minutes", "0.5000", False, {"method": "minmax", "direction": "higher"}),
    ("book", "book_count", "1.0000", False, {"method": "minmax", "direction": "higher"}),
    ("mood", "building_area", "0.3000", False, {"method": "minmax", "direction": "higher"}),
    ("nearby", "distance_m", "1.0000", False, {"method": "inverse_distance", "requires_location": True}),
    ("program", "active_program_count", "1.0000", False, {"method": "minmax", "direction": "higher"}),
]


PURPOSE_TAG_RULES = [
    ("study", "facility_reading_room", "direct", "0.7000", False),
    ("study", "many_seats", "direct", "0.7000", False),
    ("study", "review_quiet_study", "review_rollup", "0.5000", False),
    ("study", "review_focused_atmosphere", "review_rollup", "0.5000", False),
    ("study", "review_seats_sufficient", "review_rollup", "0.5000", False),
    ("study", "review_comfortable_reading_space", "review_rollup", "0.4000", False),
    ("book", "rich_collection", "direct", "0.8000", False),
    ("book", "review_books_diverse", "review_rollup", "0.6000", False),
    ("book", "review_easy_book_finding", "review_rollup", "0.4000", False),
    ("book", "review_frequent_new_books", "review_rollup", "0.4000", False),
    ("kids", "facility_children_room", "direct", "0.8000", False),
    ("kids", "children_library", "direct", "0.7000", False),
    ("kids", "review_children_friendly", "review_rollup", "0.5000", False),
    ("kids", "review_children_room_good", "review_rollup", "0.5000", False),
    ("kids", "review_family_friendly", "review_rollup", "0.5000", False),
    ("kids", "review_good_children_books", "review_rollup", "0.4000", False),
    ("kids", "review_good_children_programs", "review_rollup", "0.4000", False),
    ("mood", "facility_lounge", "direct", "0.5000", False),
    ("mood", "facility_outdoor_space", "direct", "0.5000", False),
    ("mood", "review_comfortable_space", "review_rollup", "0.5000", False),
    ("mood", "review_clean_space", "review_rollup", "0.4000", False),
    ("mood", "review_stay_friendly", "review_rollup", "0.5000", False),
    ("mood", "review_good_nearby_scenery", "review_rollup", "0.4000", False),
    ("mood", "review_outdoor_space_good", "review_rollup", "0.4000", False),
    ("program", "program_lecture_humanities", "program_rollup", "0.4000", False),
    ("program", "program_reading_writing", "program_rollup", "0.5000", False),
    ("program", "program_culture_art", "program_rollup", "0.5000", False),
    ("program", "program_experience_education", "program_rollup", "0.5000", False),
    ("program", "program_exhibition", "program_rollup", "0.3000", False),
    ("program", "review_good_programs", "review_rollup", "0.5000", False),
    ("program", "review_programs_diverse", "review_rollup", "0.4000", False),
]


DAILY_METRIC_RULES = [
    ("large_space", "building_area", "0.6000", False, {"method": "minmax", "direction": "higher"}),
    ("large_space", "site_area", "0.4000", False, {"method": "minmax", "direction": "higher"}),
    ("rich_collection", "book_count", "1.0000", False, {"method": "minmax", "direction": "higher"}),
    ("study_seats", "reading_seat_count", "1.0000", False, {"method": "minmax", "direction": "higher"}),
]


DAILY_TAG_RULES = [
    ("large_space", "review_comfortable_space", "review_rollup", "0.3000", False, {}),
    ("large_space", "review_stay_friendly", "review_rollup", "0.3000", False, {}),
    ("rich_collection", "rich_collection", "direct", "0.7000", False, {}),
    ("rich_collection", "review_books_diverse", "review_rollup", "0.5000", False, {}),
    ("mood_space", "facility_outdoor_space", "direct", "0.6000", False, {}),
    ("mood_space", "review_good_nearby_scenery", "review_rollup", "0.5000", False, {}),
    ("mood_space", "review_outdoor_space_good", "review_rollup", "0.5000", False, {}),
    ("study_seats", "many_seats", "direct", "0.6000", False, {}),
    ("study_seats", "review_quiet_study", "review_rollup", "0.5000", False, {}),
    ("study_seats", "review_focused_atmosphere", "review_rollup", "0.5000", False, {}),
    ("study_seats", "review_seats_sufficient", "review_rollup", "0.5000", False, {}),
    ("study_seats", "review_comfortable_reading_space", "review_rollup", "0.4000", False, {}),
    ("family_outing", "facility_children_room", "direct", "0.7000", False, {}),
    ("family_outing", "review_children_room_good", "review_rollup", "0.5000", False, {}),
    ("family_outing", "review_children_friendly", "review_rollup", "0.5000", False, {}),
    ("family_outing", "review_family_friendly", "review_rollup", "0.5000", False, {}),
    ("family_outing", "review_good_children_books", "review_rollup", "0.4000", False, {}),
    ("family_outing", "review_good_children_programs", "review_rollup", "0.4000", False, {}),
    ("restful_space", "facility_lounge", "direct", "0.7000", False, {}),
    ("restful_space", "review_comfortable_space", "review_rollup", "0.5000", False, {}),
    ("restful_space", "review_clean_space", "review_rollup", "0.4000", False, {}),
    ("restful_space", "review_stay_friendly", "review_rollup", "0.5000", False, {}),
]


class Command(BaseCommand):
    help = "Seed idempotent service defaults for tags, purposes, and recommendation rules."

    def handle(self, *args, **options):
        results = {}

        with transaction.atomic():
            results["Tag"] = self.seed_tags()
            results["Purpose"] = self.seed_purposes()
            results["DailyRecommendationTheme"] = self.seed_daily_themes()
            results["PurposeMetricRule"] = self.seed_purpose_metric_rules()
            results["PurposeTagRule"] = self.seed_purpose_tag_rules()
            results["DailyRecommendationMetricRule"] = self.seed_daily_metric_rules()
            results["DailyRecommendationTagRule"] = self.seed_daily_tag_rules()

        for name, result in results.items():
            self.stdout.write(f"{name}: created={result['created']} updated={result['updated']}")

    def seed_tags(self):
        result = self.empty_result()
        for (
            code,
            label,
            semantic_kind,
            tag_group,
            description,
            is_profile_selectable,
            is_review_selectable,
            review_label,
            review_group,
            is_filterable,
            display_order,
            review_display_order,
        ) in TAG_SEEDS:
            _, created = Tag.objects.update_or_create(
                code=code,
                defaults={
                    "label": label,
                    "semantic_kind": semantic_kind,
                    "tag_group": tag_group,
                    "description": description,
                    "is_profile_selectable": is_profile_selectable,
                    "is_review_selectable": is_review_selectable,
                    "review_label": review_label,
                    "review_group": review_group,
                    "is_filterable": is_filterable,
                    "display_order": display_order,
                    "review_display_order": review_display_order,
                    "is_active": True,
                },
            )
            self.count(result, created)
        return result

    def seed_purposes(self):
        result = self.empty_result()
        for code, label, description, display_order, is_home_theme, is_profile_selectable, analysis_axis, requires_location in PURPOSE_SEEDS:
            _, created = Purpose.objects.update_or_create(
                code=code,
                defaults={
                    "label": label,
                    "description": description,
                    "display_order": display_order,
                    "is_home_theme": is_home_theme,
                    "is_profile_selectable": is_profile_selectable,
                    "analysis_axis": analysis_axis,
                    "requires_location": requires_location,
                    "is_active": True,
                },
            )
            self.count(result, created)
        return result

    def seed_daily_themes(self):
        result = self.empty_result()
        for code, label, subtitle, description, display_order in DAILY_THEME_SEEDS:
            _, created = DailyRecommendationTheme.objects.update_or_create(
                code=code,
                defaults={
                    "label": label,
                    "subtitle": subtitle,
                    "description": description,
                    "display_order": display_order,
                    "is_active": True,
                },
            )
            self.count(result, created)
        return result

    def seed_purpose_metric_rules(self):
        result = self.empty_result()
        purposes = self.purpose_map()
        for purpose_code, metric_code, weight, is_required, normalization_rule in PURPOSE_METRIC_RULES:
            _, created = PurposeMetricRule.objects.update_or_create(
                purpose=purposes[purpose_code],
                metric_code=metric_code,
                defaults={
                    "weight": weight,
                    "is_required": is_required,
                    "normalization_rule": normalization_rule,
                },
            )
            self.count(result, created)
        return result

    def seed_purpose_tag_rules(self):
        result = self.empty_result()
        purposes = self.purpose_map()
        tags = self.tag_map()
        for purpose_code, tag_code, source_scope, weight, is_required in PURPOSE_TAG_RULES:
            _, created = PurposeTagRule.objects.update_or_create(
                purpose=purposes[purpose_code],
                tag=tags[tag_code],
                source_scope=source_scope,
                defaults={
                    "weight": weight,
                    "is_required": is_required,
                },
            )
            self.count(result, created)
        return result

    def seed_daily_metric_rules(self):
        result = self.empty_result()
        themes = self.daily_theme_map()
        for theme_code, metric_code, weight, is_required, normalization_rule in DAILY_METRIC_RULES:
            _, created = DailyRecommendationMetricRule.objects.update_or_create(
                theme=themes[theme_code],
                metric_code=metric_code,
                defaults={
                    "weight": weight,
                    "is_required": is_required,
                    "normalization_rule": normalization_rule,
                },
            )
            self.count(result, created)
        return result

    def seed_daily_tag_rules(self):
        result = self.empty_result()
        themes = self.daily_theme_map()
        tags = self.tag_map()
        for theme_code, tag_code, source_scope, weight, is_required, normalization_rule in DAILY_TAG_RULES:
            _, created = DailyRecommendationTagRule.objects.update_or_create(
                theme=themes[theme_code],
                tag=tags[tag_code],
                source_scope=source_scope,
                defaults={
                    "weight": weight,
                    "is_required": is_required,
                    "normalization_rule": normalization_rule,
                },
            )
            self.count(result, created)
        return result

    def tag_map(self):
        return {tag.code: tag for tag in Tag.objects.filter(code__in=[seed[0] for seed in TAG_SEEDS])}

    def purpose_map(self):
        return {purpose.code: purpose for purpose in Purpose.objects.filter(code__in=[seed[0] for seed in PURPOSE_SEEDS])}

    def daily_theme_map(self):
        return {
            theme.code: theme
            for theme in DailyRecommendationTheme.objects.filter(code__in=[seed[0] for seed in DAILY_THEME_SEEDS])
        }

    @staticmethod
    def empty_result():
        return {"created": 0, "updated": 0}

    @staticmethod
    def count(result, created):
        if created:
            result["created"] += 1
        else:
            result["updated"] += 1
