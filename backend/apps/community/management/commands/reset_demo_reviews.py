from __future__ import annotations

import shutil
import zipfile
from dataclasses import dataclass
from pathlib import Path

from django.conf import settings
from django.contrib.auth import get_user_model
from django.core.management.base import BaseCommand, CommandError
from django.db import transaction
from django.utils import timezone

from apps.accounts.models import UserProfile
from apps.books.models import Book
from apps.community.models import (
    ReviewBookReference,
    ReviewProgramReference,
    ReviewTag,
    UserReview,
    UserReviewImage,
    UserReviewLike,
)
from apps.libraries.models import Library
from apps.preferences.services import rebuild_user_preference
from apps.programs.models import (
    ApplicationStatus,
    OperationStatus,
    Program,
    ProgramCategory,
)
from apps.tags.models import Tag, TagSemanticKind


DEMO_EMAIL_DOMAIN = "library-outing.local"
DEMO_LIKER_COUNT = 15
DEMO_IMAGE_DIR = "reviews/demo"

TAG_ALIASES = {
    "review_clear_guidance": "review_kind_guidance",
    "review_collection_good": "review_books_diverse",
    "review_easy_access": "review_easy_to_visit",
    "review_family_visit": "review_family_friendly",
    "review_reading_writing_program": "review_program_reading_writing_good",
}

IMAGE_MAPPINGS = {
    "김나들이_01.png": "reviews/demo/demo_review_01.png",
    "책산책_01.png": "reviews/demo/demo_review_02.png",
    "부산책방문자_01.png": "reviews/demo/demo_review_03.png",
    "나들이초보_01.png": "reviews/demo/demo_review_04.png",
    "나들이초보_02.png": "reviews/demo/demo_review_05.png",
    "나들이초보_03.png": "reviews/demo/demo_review_06.png",
    "조용한서가_01.png": "reviews/demo/demo_review_07.png",
    "조용한서가_02.png": "reviews/demo/demo_review_08.png",
}

UNUSED_ZIP_IMAGES = {
    "책산책_01_추가.png",
    "책산책_02_추가.png",
    "부산책방문자_02.png",
    "노트북들고_01.png",
}


@dataclass(frozen=True)
class DemoReviewImage:
    source_name: str
    target_path: str
    alt_text: str


REVIEW_BLUEPRINTS = [
    {
        "user_nickname": "김나들이",
        "library_name": "부산광역시립해운대도서관",
        "sigungu": "해운대구",
        "content": "생각보다 공간이 넓고 조용해서 오래 앉아 있기 좋았어요. 시험 기간에 다시 와도 괜찮겠다는 생각이 들었습니다.",
        "tag_codes": ["review_quiet_study", "review_seats_sufficient", "review_comfortable_space"],
        "related_books": [],
        "related_programs": [],
        "images": [
            DemoReviewImage("김나들이_01.png", IMAGE_MAPPINGS["김나들이_01.png"], "부산광역시립해운대도서관의 조용한 열람 공간"),
        ],
        "view_count": 48,
        "like_count": 12,
    },
    {
        "user_nickname": "책산책",
        "library_name": "재송어린이도서관",
        "sigungu": "해운대구",
        "content": "아이랑 같이 갔는데 어린이자료실이 아늑해서 좋았어요. 책 고르는 동안 아이가 지루해하지 않아서 주말에 들르기 괜찮았습니다.",
        "tag_codes": ["review_children_friendly", "review_children_room_good", "review_family_visit"],
        "related_books": [],
        "related_programs": [],
        "images": [
            DemoReviewImage("책산책_01.png", IMAGE_MAPPINGS["책산책_01.png"], "재송어린이도서관의 어린이자료실 분위기"),
        ],
        "view_count": 36,
        "like_count": 8,
    },
    {
        "user_nickname": "부산책방문자",
        "library_name": "해운대인문학도서관",
        "sigungu": "해운대구",
        "content": "창가 쪽 자리가 편안했고 전체적으로 분위기가 차분했어요. 책을 빌리지 않아도 잠깐 머물다 가기 좋은 곳이었습니다.",
        "tag_codes": ["review_comfortable_space", "review_clean_space", "review_stay_friendly"],
        "related_books": [],
        "related_programs": [],
        "images": [
            DemoReviewImage("부산책방문자_01.png", IMAGE_MAPPINGS["부산책방문자_01.png"], "해운대인문학도서관의 창가 좌석과 휴게 공간"),
        ],
        "view_count": 41,
        "like_count": 11,
    },
    {
        "user_nickname": "나들이초보",
        "library_name": "다대도서관",
        "sigungu": "사하구",
        "content": "독서 프로그램에 참여했는데 진행이 차분하고 안내가 친절했어요. 처음 참여하는 사람도 부담 없이 따라갈 수 있었습니다.",
        "tag_codes": ["review_good_programs", "review_kind_guidance", "review_reading_writing_program"],
        "related_books": [],
        "related_programs": ["책 소풍 가는 날"],
        "images": [
            DemoReviewImage("나들이초보_01.png", IMAGE_MAPPINGS["나들이초보_01.png"], "다대도서관 프로그램 안내판"),
            DemoReviewImage("나들이초보_02.png", IMAGE_MAPPINGS["나들이초보_02.png"], "다대도서관 프로그램 강의실"),
            DemoReviewImage("나들이초보_03.png", IMAGE_MAPPINGS["나들이초보_03.png"], "다대도서관 프로그램 활동 자료"),
        ],
        "view_count": 52,
        "like_count": 15,
    },
    {
        "user_nickname": "조용한서가",
        "library_name": "화명도서관",
        "sigungu": "북구",
        "content": "관심 있던 분야 책이 꽤 다양해서 둘러보는 재미가 있었어요. 서가 안내도 어렵지 않아서 원하는 책을 금방 찾았습니다.",
        "tag_codes": ["review_books_diverse", "review_easy_book_finding", "review_collection_good"],
        "related_books": ["아몬드", "불편한 편의점"],
        "related_programs": [],
        "images": [
            DemoReviewImage("조용한서가_01.png", IMAGE_MAPPINGS["조용한서가_01.png"], "화명도서관의 서가"),
            DemoReviewImage("조용한서가_02.png", IMAGE_MAPPINGS["조용한서가_02.png"], "화명도서관에서 고른 책"),
        ],
        "view_count": 44,
        "like_count": 10,
    },
    {
        "user_nickname": "김나들이",
        "library_name": "부산광역시립시민도서관",
        "sigungu": "부산진구",
        "content": "대중교통으로 가기 편했고 처음 방문했는데도 동선이 크게 어렵지 않았어요. 필요한 공간을 찾기 쉬운 편이었습니다.",
        "tag_codes": ["review_easy_access", "review_clear_guidance"],
        "related_books": [],
        "related_programs": [],
        "images": [],
        "view_count": 27,
        "like_count": 5,
    },
    {
        "user_nickname": "책산책",
        "library_name": "부산영어도서관",
        "sigungu": "부산진구",
        "content": "영어 원서가 궁금해서 방문했는데 생각보다 자료가 잘 정리되어 있었어요. 가볍게 영어책을 골라보기 좋은 곳이었습니다.",
        "tag_codes": ["review_books_diverse", "review_easy_book_finding"],
        "related_books": ["Wonder"],
        "related_programs": [],
        "images": [],
        "view_count": 22,
        "like_count": 4,
    },
    {
        "user_nickname": "노트북들고",
        "library_name": "금샘도서관",
        "sigungu": "금정구",
        "content": "노트북으로 작업하기 괜찮았고 와이파이도 무난하게 연결됐어요. 짧게 집중해서 할 일을 정리하기 좋은 분위기였습니다.",
        "tag_codes": ["review_laptop_friendly", "review_wifi_reliable", "review_quiet_study"],
        "related_books": [],
        "related_programs": [],
        "images": [],
        "view_count": 31,
        "like_count": 7,
    },
    {
        "user_nickname": "부산책방문자",
        "library_name": "금정도서관",
        "sigungu": "금정구",
        "content": "차를 가지고 갔는데 주차가 생각보다 불편하지 않았어요. 가족이랑 같이 움직일 때 후보로 넣어둘 만한 도서관입니다.",
        "tag_codes": ["review_parking_convenient", "review_family_visit", "review_easy_access"],
        "related_books": [],
        "related_programs": [],
        "images": [],
        "view_count": 19,
        "like_count": 3,
    },
    {
        "user_nickname": "나들이초보",
        "library_name": "연제만화도서관",
        "sigungu": "연제구",
        "content": "만화 자료가 있어서 분위기가 조금 더 편하게 느껴졌어요. 조용히 읽고 가기에도 좋고 부담 없이 들르기 괜찮았습니다.",
        "tag_codes": ["review_collection_good", "review_comfortable_space", "review_stay_friendly"],
        "related_books": [],
        "related_programs": [],
        "images": [],
        "view_count": 25,
        "like_count": 6,
    },
    {
        "user_nickname": "책산책",
        "library_name": "부산진구기적의도서관",
        "sigungu": "부산진구",
        "content": "어린이 프로그램을 보러 갔는데 공간이 밝고 안내도 잘 되어 있었어요. 아이와 처음 방문하기에도 부담이 적었습니다.",
        "tag_codes": ["review_children_friendly", "review_good_programs", "review_kind_guidance"],
        "related_books": [],
        "related_programs": ["그림책으로 만나는 주말"],
        "images": [],
        "view_count": 33,
        "like_count": 9,
    },
    {
        "user_nickname": "조용한서가",
        "library_name": "부산광역시립구포도서관",
        "sigungu": "북구",
        "content": "규모가 있어서 그런지 자료가 풍부하게 느껴졌어요. 오래 머물기보다는 책을 찾고 빌리러 가기에 만족스러웠습니다.",
        "tag_codes": ["review_books_diverse", "review_collection_good"],
        "related_books": ["도시와 그 불확실한 벽"],
        "related_programs": [],
        "images": [],
        "view_count": 16,
        "like_count": 2,
    },
]


BOOK_DEFAULTS = {
    "Wonder": {
        "title": "Wonder",
        "authors_text": "R. J. Palacio",
        "publisher": "Knopf Books for Young Readers",
        "publication_year": 2012,
        "kdc_class_name": "문학",
        "provider_code": "demo",
    },
    "도시와 그 불확실한 벽": {
        "title": "도시와 그 불확실한 벽",
        "authors_text": "무라카미 하루키",
        "publisher": "문학동네",
        "publication_year": 2023,
        "kdc_class_name": "문학",
        "provider_code": "demo",
    },
}


class BaseCommandError(CommandError):
    pass


class Command(BaseCommand):
    help = "Reset only review-related data and create polished demo reviews with valid media."

    def add_arguments(self, parser):
        parser.add_argument(
            "--image-zip",
            required=True,
            help="Path to the zip file containing demo review images.",
        )
        parser.add_argument(
            "--dry-run",
            action="store_true",
            help="Validate and print the planned reset without changing database rows or media files.",
        )

    def handle(self, *args, **options):
        image_zip = Path(options["image_zip"])
        dry_run = options["dry_run"]

        before_counts = self.get_counts()
        before_images = self.collect_existing_review_images()
        zip_names = self.validate_image_zip(image_zip)
        libraries = self.resolve_libraries()
        tags = self.resolve_tags()
        books = self.resolve_books()
        programs = self.resolve_programs(libraries)
        planned_images = self.plan_images(zip_names)

        self.print_plan(before_counts, before_images, planned_images, books, programs)
        if dry_run:
            self.stdout.write(self.style.WARNING("dry-run: no database rows or media files changed."))
            return

        with transaction.atomic():
            affected_user_ids = set(UserReview.objects.values_list("user_id", flat=True))
            deleted_counts = UserReview.objects.all().delete()[1]
            authors = self.ensure_author_users()
            liker_users = self.ensure_liker_users()
            created_books = self.ensure_books(books)
            created_programs = self.ensure_programs(programs, libraries)
            created_reviews = self.create_reviews(
                authors=authors,
                liker_users=liker_users,
                libraries=libraries,
                tags=tags,
                books=created_books,
                programs=created_programs,
            )
            affected_user_ids.update(user.id for user in authors.values())
            affected_user_ids.update(user.id for user in liker_users)

        deleted_files = self.delete_existing_review_media(before_images)
        copied_images = self.copy_demo_images(image_zip)
        self.rebuild_preferences(affected_user_ids)

        self.print_result(deleted_counts, deleted_files, copied_images, created_reviews)

    def get_counts(self):
        return {
            "UserReview": UserReview.objects.count(),
            "UserReviewImage": UserReviewImage.objects.count(),
            "UserReviewLike": UserReviewLike.objects.count(),
            "ReviewTag": ReviewTag.objects.count(),
            "ReviewBookReference": ReviewBookReference.objects.count(),
            "ReviewProgramReference": ReviewProgramReference.objects.count(),
        }

    def collect_existing_review_images(self):
        return [
            value
            for value in UserReviewImage.objects.exclude(image="").exclude(image__isnull=True).values_list(
                "image",
                flat=True,
            )
        ]

    def validate_image_zip(self, image_zip):
        if not image_zip.exists():
            raise CommandError(f"image zip does not exist: {image_zip}")
        if not zipfile.is_zipfile(image_zip):
            raise CommandError(f"image zip is not a valid zip file: {image_zip}")

        with zipfile.ZipFile(image_zip) as archive:
            names = {Path(info.filename).name for info in archive.infolist() if not info.is_dir()}

        required = set(IMAGE_MAPPINGS)
        missing = sorted(required - names)
        if missing:
            raise CommandError("missing required images in zip:\n" + "\n".join(f"- {name}" for name in missing))
        return names

    def resolve_libraries(self):
        libraries = {}
        missing = []
        for blueprint in REVIEW_BLUEPRINTS:
            key = (blueprint["library_name"], blueprint["sigungu"])
            if key in libraries:
                continue
            library = Library.objects.filter(
                is_active=True,
                name=blueprint["library_name"],
                sigungu=blueprint["sigungu"],
            ).first()
            if library:
                libraries[key] = library
            else:
                missing.append(f"{blueprint['library_name']} ({blueprint['sigungu']})")
        if missing:
            raise CommandError("missing demo libraries:\n" + "\n".join(f"- {item}" for item in missing))
        return libraries

    def resolve_tags(self):
        requested_codes = {
            TAG_ALIASES.get(tag_code, tag_code)
            for blueprint in REVIEW_BLUEPRINTS
            for tag_code in blueprint["tag_codes"]
        }
        tags = {
            tag.code: tag
            for tag in Tag.objects.filter(
                code__in=requested_codes,
                is_active=True,
                is_review_selectable=True,
                semantic_kind=TagSemanticKind.EXPERIENCE,
            )
        }
        missing = sorted(requested_codes - set(tags))
        if missing:
            raise CommandError("missing selectable review tags:\n" + "\n".join(f"- {code}" for code in missing))
        return tags

    def resolve_books(self):
        titles = {title for blueprint in REVIEW_BLUEPRINTS for title in blueprint["related_books"]}
        resolved = {}
        for title in titles:
            book = Book.objects.filter(is_active=True, title__icontains=title).order_by("id").first()
            if book:
                resolved[title] = {"book": book, "create": False}
            elif title in BOOK_DEFAULTS:
                resolved[title] = {"book": None, "create": True}
            else:
                raise CommandError(f"missing demo book and no default is configured: {title}")
        return resolved

    def resolve_programs(self, libraries):
        titles = {title for blueprint in REVIEW_BLUEPRINTS for title in blueprint["related_programs"]}
        resolved = {}
        for title in titles:
            blueprint = next(item for item in REVIEW_BLUEPRINTS if title in item["related_programs"])
            library = libraries[(blueprint["library_name"], blueprint["sigungu"])]
            program = Program.objects.filter(
                title__icontains=title,
                library=library,
                is_visible=True,
                deleted_at__isnull=True,
            ).order_by("id").first()
            resolved[title] = {"program": program, "library": library, "create": program is None}
        return resolved

    def plan_images(self, zip_names):
        planned = []
        for blueprint in REVIEW_BLUEPRINTS:
            for image in blueprint["images"]:
                planned.append(image)
        planned_sources = {image.source_name for image in planned}
        unused_present = sorted(UNUSED_ZIP_IMAGES & zip_names)
        self.stdout.write(f"unused images present in zip: {len(unused_present)}")
        for name in unused_present:
            self.stdout.write(f"- unused: {name}")
        return planned

    def ensure_author_users(self):
        user_model = get_user_model()
        users = {}
        for nickname in sorted({blueprint["user_nickname"] for blueprint in REVIEW_BLUEPRINTS}):
            email = f"demo.review.{slugify_korean(nickname)}@{DEMO_EMAIL_DOMAIN}"
            user, created = user_model.objects.get_or_create(email=email, defaults={"nickname": nickname})
            update_fields = []
            if user.nickname != nickname:
                user.nickname = nickname
                update_fields.append("nickname")
            if created or not user.has_usable_password():
                user.set_unusable_password()
                update_fields.append("password")
            if update_fields:
                user.save(update_fields=update_fields)
            UserProfile.objects.get_or_create(user=user)
            users[nickname] = user
        return users

    def ensure_liker_users(self):
        user_model = get_user_model()
        users = []
        for index in range(1, DEMO_LIKER_COUNT + 1):
            email = f"demo.like.{index:02d}@{DEMO_EMAIL_DOMAIN}"
            nickname = f"시연좋아요{index:02d}"
            user, created = user_model.objects.get_or_create(email=email, defaults={"nickname": nickname})
            update_fields = []
            if user.nickname != nickname:
                user.nickname = nickname
                update_fields.append("nickname")
            if created or not user.has_usable_password():
                user.set_unusable_password()
                update_fields.append("password")
            if update_fields:
                user.save(update_fields=update_fields)
            UserProfile.objects.get_or_create(user=user)
            users.append(user)
        return users

    def ensure_books(self, resolved):
        books = {}
        for title, data in resolved.items():
            if data["book"]:
                books[title] = data["book"]
                continue
            defaults = BOOK_DEFAULTS[title]
            book = Book.objects.create(**defaults)
            books[title] = book
        return books

    def ensure_programs(self, resolved, libraries):
        programs = {}
        for title, data in resolved.items():
            if data["program"]:
                programs[title] = data["program"]
                continue
            library = data["library"]
            program = Program.objects.create(
                library=library,
                source_sido="부산광역시",
                source_sigungu=library.sigungu,
                source_library_name=library.name,
                provider_code="demo",
                external_program_key=f"demo-review-{library.id}-{slugify_korean(title)}",
                title=title,
                category_code=ProgramCategory.READING_WRITING,
                target_text="전체",
                target_codes=["all"],
                application_required=False,
                application_status=ApplicationStatus.NOT_REQUIRED,
                operation_start_date=timezone.localdate(),
                operation_end_date=timezone.localdate(),
                operation_status=OperationStatus.ONGOING,
                source_board="demo",
                is_visible=True,
            )
            programs[title] = program
        return programs

    def create_reviews(self, *, authors, liker_users, libraries, tags, books, programs):
        created_reviews = []
        for blueprint in REVIEW_BLUEPRINTS:
            library = libraries[(blueprint["library_name"], blueprint["sigungu"])]
            review = UserReview.objects.create(
                user=authors[blueprint["user_nickname"]],
                library=library,
                content=blueprint["content"],
                view_count=blueprint["view_count"],
                like_count=0,
            )
            self.create_review_tags(review, blueprint, tags)
            self.create_review_books(review, blueprint, books)
            self.create_review_programs(review, blueprint, programs)
            self.create_review_images(review, blueprint)
            self.create_review_likes(review, liker_users, blueprint["like_count"])
            created_reviews.append(review)
        return created_reviews

    def create_review_tags(self, review, blueprint, tags):
        seen = set()
        for tag_code in blueprint["tag_codes"]:
            resolved_code = TAG_ALIASES.get(tag_code, tag_code)
            if resolved_code in seen:
                continue
            seen.add(resolved_code)
            ReviewTag.objects.create(review=review, tag=tags[resolved_code])

    def create_review_books(self, review, blueprint, books):
        for index, title in enumerate(blueprint["related_books"]):
            ReviewBookReference.objects.create(review=review, book=books[title], display_order=index)

    def create_review_programs(self, review, blueprint, programs):
        for index, title in enumerate(blueprint["related_programs"]):
            program = programs[title]
            if program.library_id != review.library_id:
                raise CommandError(f"program library mismatch: {title}")
            ReviewProgramReference.objects.create(review=review, program=program, display_order=index)

    def create_review_images(self, review, blueprint):
        for index, image in enumerate(blueprint["images"]):
            UserReviewImage.objects.create(
                review=review,
                image=image.target_path,
                alt_text=image.alt_text,
                display_order=index,
            )

    def create_review_likes(self, review, liker_users, like_count):
        for user in liker_users[:like_count]:
            UserReviewLike.objects.create(user=user, review=review)
        review.like_count = review.likes.count()
        review.save(update_fields=["like_count", "updated_at"])

    def delete_existing_review_media(self, image_paths):
        deleted = []
        skipped = []
        media_root = Path(settings.MEDIA_ROOT).resolve()
        for image_path in sorted(set(image_paths)):
            result = resolve_media_path(media_root, image_path)
            if result is None:
                skipped.append(image_path)
                continue
            if result.exists() and result.is_file():
                result.unlink()
                deleted.append(image_path)
            else:
                skipped.append(image_path)
        self.stdout.write(f"deleted old review media files: {len(deleted)}")
        for image_path in deleted:
            self.stdout.write(f"- deleted media: {image_path}")
        for image_path in skipped:
            self.stdout.write(f"- skipped media: {image_path}")
        return deleted

    def copy_demo_images(self, image_zip):
        copied = []
        with zipfile.ZipFile(image_zip) as archive:
            by_name = {Path(info.filename).name: info for info in archive.infolist() if not info.is_dir()}
            for source_name, target_path in IMAGE_MAPPINGS.items():
                target = Path(settings.MEDIA_ROOT) / target_path
                target.parent.mkdir(parents=True, exist_ok=True)
                with archive.open(by_name[source_name]) as source, target.open("wb") as destination:
                    shutil.copyfileobj(source, destination)
                copied.append(target_path)
        return copied

    def rebuild_preferences(self, user_ids):
        user_model = get_user_model()
        for user in user_model.objects.filter(id__in=user_ids):
            rebuild_user_preference(user)

    def print_plan(self, before_counts, before_images, planned_images, books, programs):
        self.stdout.write("current review data counts:")
        for key, value in before_counts.items():
            self.stdout.write(f"- {key}: {value}")
        self.stdout.write(f"existing referenced review media files: {len(before_images)}")
        for image_path in before_images:
            self.stdout.write(f"- old media: {image_path}")
        self.stdout.write(f"planned demo reviews: {len(REVIEW_BLUEPRINTS)}")
        self.stdout.write(f"planned demo images: {len(planned_images)}")
        self.stdout.write("book references:")
        for title, data in sorted(books.items()):
            action = "reuse" if data["book"] else "create"
            self.stdout.write(f"- {action}: {title}")
        self.stdout.write("program references:")
        for title, data in sorted(programs.items()):
            action = "reuse" if data["program"] else "create"
            self.stdout.write(f"- {action}: {title} @ {data['library'].name}")

    def print_result(self, deleted_counts, deleted_files, copied_images, created_reviews):
        self.stdout.write("deleted rows by model:")
        for model_name, count in sorted(deleted_counts.items()):
            self.stdout.write(f"- {model_name}: {count}")
        self.stdout.write("copied demo media files:")
        for image_path in copied_images:
            self.stdout.write(f"- {image_path}")
        self.stdout.write(f"created demo reviews: {len(created_reviews)}")
        self.stdout.write(f"created image rows: {UserReviewImage.objects.count()}")
        self.stdout.write(f"image-included reviews: {UserReview.objects.filter(images__isnull=False).distinct().count()}")
        self.stdout.write(f"deleted old media file count: {len(deleted_files)}")


def resolve_media_path(media_root, image_path):
    raw = str(image_path or "")
    if not raw or raw.startswith(("http://", "https://")):
        return None
    candidate = (media_root / raw).resolve()
    try:
        candidate.relative_to(media_root)
    except ValueError:
        return None
    return candidate


def slugify_korean(value):
    replacements = {
        "김나들이": "kim-nadeuli",
        "책산책": "book-walk",
        "부산책방문자": "busan-book-visitor",
        "나들이초보": "outing-starter",
        "조용한서가": "quiet-shelf",
        "노트북들고": "with-laptop",
        "책 소풍 가는 날": "book-picnic-day",
        "그림책으로 만나는 주말": "picture-book-weekend",
    }
    if value in replacements:
        return replacements[value]
    return "-".join(str(value).strip().lower().split())
