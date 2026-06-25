from pathlib import Path
import shutil

from django.conf import settings
from django.contrib.auth import get_user_model
from django.core.management.base import BaseCommand, CommandError
from django.db import transaction

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
from apps.programs.models import Program
from apps.tags.models import Tag, TagSemanticKind


SOURCE_IMAGE_DIR = (
    settings.BASE_DIR / "apps" / "media_assets" / "static" / "media_assets" / "placeholders"
)

DEMO_USERS = [
    {
        "email": "demo.reviewer@library-outing.local",
        "nickname": "시연 나들이",
    },
    {
        "email": "demo.friend@library-outing.local",
        "nickname": "시연 친구",
    },
]

DEMO_IMAGE_SOURCES = {
    "reviews/demo/demo_review_study_01.png": "default_library_public.png",
    "reviews/demo/demo_review_kids_01.png": "default_library_children.png",
    "reviews/demo/demo_review_mood_01.png": "default_library_small.png",
    "reviews/demo/demo_review_program_01.png": "default_program_reading.png",
}

REVIEW_BLUEPRINTS = [
    {
        "key": "study",
        "content": "방문했을 때 분위기가 차분해서 해야 할 일을 정리하기 좋았어요. 짧게 머물러도 집중이 잘 되는 느낌이었습니다.",
        "tag_codes": ["review_quiet_study", "review_focused_atmosphere", "review_comfortable_reading_space"],
        "image": "reviews/demo/demo_review_study_01.png",
        "alt_text": "차분한 도서관 열람 분위기 예시 이미지",
        "book": True,
    },
    {
        "key": "kids",
        "content": "아이와 함께 책을 고르기 편했고 직원 안내도 친절했습니다. 주말에 가볍게 들르기 좋은 도서관이었어요.",
        "tag_codes": ["review_children_friendly", "review_good_children_books", "review_kind_guidance"],
        "image": "reviews/demo/demo_review_kids_01.png",
        "alt_text": "아이와 방문한 도서관 분위기 예시 이미지",
        "book": True,
    },
    {
        "key": "books",
        "content": "책장을 천천히 둘러보는 재미가 있었고 관심 가는 책을 찾기 쉬웠습니다. 다음에도 책 빌리러 오고 싶어요.",
        "tag_codes": ["review_books_diverse", "review_easy_book_finding", "review_frequent_new_books"],
        "book": True,
    },
    {
        "key": "program",
        "content": "프로그램 안내가 보기 쉬웠고 진행 분위기도 편안했습니다. 도서관을 처음 방문하는 사람도 부담이 적을 것 같아요.",
        "tag_codes": ["review_good_programs", "review_program_reading_writing_good", "review_kind_guidance"],
        "image": "reviews/demo/demo_review_program_01.png",
        "alt_text": "도서관 문화 프로그램 안내 예시 이미지",
        "program": True,
    },
    {
        "key": "mood",
        "content": "전체적으로 공간이 깔끔하게 관리되어 있어서 머무는 동안 편했습니다. 잠깐 쉬며 책 읽기에 좋았어요.",
        "tag_codes": ["review_clean_space", "review_comfortable_space", "review_well_managed"],
        "image": "reviews/demo/demo_review_mood_01.png",
        "alt_text": "깔끔한 도서관 공간 분위기 예시 이미지",
    },
    {
        "key": "access",
        "content": "동네에서 들르기 부담 없는 위치라 일정을 마치고 잠깐 방문하기 좋았습니다. 책 찾는 동선도 편했어요.",
        "tag_codes": ["review_easy_to_visit", "review_public_transport_access", "review_easy_book_finding"],
    },
    {
        "key": "guide",
        "content": "처음 이용하는 자료를 찾고 있었는데 안내를 친절하게 받아서 금방 적응했습니다. 관리도 잘 되는 느낌이었어요.",
        "tag_codes": ["review_kind_guidance", "review_well_managed", "review_easy_book_finding"],
        "book": True,
    },
    {
        "key": "local",
        "content": "산책하다 들러 조용히 책을 읽고 왔습니다. 가까운 곳에 이런 공간이 있다는 점이 마음에 들었어요.",
        "tag_codes": ["review_comfortable_space", "review_stay_friendly", "review_easy_to_visit"],
    },
    {
        "key": "family",
        "content": "가족이 함께 방문해도 각자 읽을 책을 고르기 괜찮았습니다. 분위기가 편안해서 오래 머물고 싶었어요.",
        "tag_codes": ["review_family_friendly", "review_books_diverse", "review_comfortable_space"],
        "book": True,
    },
    {
        "key": "program_kids",
        "content": "어린이 대상 프로그램을 살펴보기 좋았고 일정 확인도 어렵지 않았습니다. 아이와 다시 방문해 보고 싶어요.",
        "tag_codes": ["review_good_children_programs", "review_programs_diverse", "review_children_friendly"],
        "program": True,
    },
]


class Command(BaseCommand):
    help = "Reset only review-related data and create demo reviews with valid media files."

    def add_arguments(self, parser):
        parser.add_argument(
            "--dry-run",
            action="store_true",
            help="Show the planned reset without changing the database or copying media files.",
        )

    def handle(self, *args, **options):
        dry_run = options["dry_run"]
        before_counts = self.get_counts()
        before_image_paths = self.get_review_image_paths()
        missing_before = self.find_missing_media(before_image_paths)
        source_images = self.validate_source_images()

        tags_by_code = self.get_review_tags()
        libraries = self.pick_libraries()
        books = self.pick_books()
        programs = self.pick_programs()
        self.validate_blueprints(tags_by_code, libraries, books, programs)

        if dry_run:
            self.stdout.write("dry-run: no database rows changed and no media files copied.")
            self.print_summary(before_counts, missing_before, [], [], [], [])
            return

        copied_images = self.copy_demo_images(source_images)

        with transaction.atomic():
            affected_users = set(UserReview.objects.values_list("user_id", flat=True))
            deleted_counts = UserReview.objects.all().delete()[1]
            demo_users = self.ensure_demo_users()
            created_reviews = self.create_demo_reviews(demo_users, libraries, books, programs, tags_by_code)
            affected_users.update(user.id for user in demo_users)

        # Keep preference/dashboard derived data in sync after the review reset.
        user_model = get_user_model()
        for user in user_model.objects.filter(id__in=affected_users):
            rebuild_user_preference(user)

        orphan_files = self.find_orphan_files(before_image_paths)
        after_counts = self.get_counts()
        self.print_summary(after_counts, missing_before, deleted_counts, copied_images, created_reviews, orphan_files)

    def get_counts(self):
        return {
            "UserReview": UserReview.objects.count(),
            "UserReviewImage": UserReviewImage.objects.count(),
            "UserReviewLike": UserReviewLike.objects.count(),
            "ReviewTag": ReviewTag.objects.count(),
            "ReviewBookReference": ReviewBookReference.objects.count(),
            "ReviewProgramReference": ReviewProgramReference.objects.count(),
        }

    def get_review_image_paths(self):
        return [
            image
            for image in UserReviewImage.objects.exclude(image="").exclude(image__isnull=True).values_list(
                "image", flat=True
            )
        ]

    def find_missing_media(self, image_paths):
        missing = []
        for image_path in image_paths:
            if self.is_external_path(image_path):
                continue
            candidate = Path(settings.MEDIA_ROOT) / image_path
            if not candidate.exists():
                missing.append(image_path)
        return missing

    def find_orphan_files(self, before_image_paths):
        referenced = set(self.get_review_image_paths())
        orphan_files = []
        for image_path in before_image_paths:
            if self.is_external_path(image_path):
                continue
            candidate = Path(settings.MEDIA_ROOT) / image_path
            if candidate.exists() and image_path not in referenced:
                orphan_files.append(image_path)
        return sorted(set(orphan_files))

    @staticmethod
    def is_external_path(image_path):
        return str(image_path).startswith(("http://", "https://"))

    def validate_source_images(self):
        sources = {}
        missing = []
        for relative_path, source_name in DEMO_IMAGE_SOURCES.items():
            source_path = SOURCE_IMAGE_DIR / source_name
            if source_path.exists():
                sources[relative_path] = source_path
            else:
                missing.append(str(source_path))
        if missing:
            raise CommandError(
                "Missing source demo image files:\n" + "\n".join(f"- {path}" for path in missing)
            )
        return sources

    def get_review_tags(self):
        return {
            tag.code: tag
            for tag in Tag.objects.filter(
                is_active=True,
                is_review_selectable=True,
                semantic_kind=TagSemanticKind.EXPERIENCE,
            )
        }

    def pick_libraries(self):
        program_library_ids = list(
            Program.objects.filter(is_visible=True, deleted_at__isnull=True, library__is_active=True)
            .order_by("library_id", "id")
            .values_list("library_id", flat=True)
            .distinct()[:10]
        )
        libraries = list(Library.objects.filter(id__in=program_library_ids, is_active=True).order_by("id"))
        if len(libraries) < len(REVIEW_BLUEPRINTS):
            existing_ids = [library.id for library in libraries]
            libraries.extend(
                Library.objects.filter(is_active=True)
                .exclude(id__in=existing_ids)
                .order_by("id")[: len(REVIEW_BLUEPRINTS) - len(libraries)]
            )
        return libraries[: len(REVIEW_BLUEPRINTS)]

    def pick_books(self):
        return list(Book.objects.filter(is_active=True).exclude(isbn13="").order_by("title", "id")[:8])

    def pick_programs(self):
        return list(
            Program.objects.filter(is_visible=True, deleted_at__isnull=True, library__is_active=True)
            .select_related("library")
            .order_by("library_id", "id")[:8]
        )

    def validate_blueprints(self, tags_by_code, libraries, books, programs):
        if len(libraries) < len(REVIEW_BLUEPRINTS):
            raise CommandError("Not enough active libraries to create demo reviews.")
        if not books:
            raise CommandError("No active books with isbn13 are available for demo review references.")
        if not programs:
            raise CommandError("No visible programs are available for demo review references.")
        missing_tags = sorted(
            {
                tag_code
                for blueprint in REVIEW_BLUEPRINTS
                for tag_code in blueprint["tag_codes"]
                if tag_code not in tags_by_code
            }
        )
        if missing_tags:
            raise CommandError(
                "Missing selectable review tags:\n" + "\n".join(f"- {code}" for code in missing_tags)
            )

    def copy_demo_images(self, source_images):
        copied = []
        for relative_path, source_path in source_images.items():
            destination = Path(settings.MEDIA_ROOT) / relative_path
            destination.parent.mkdir(parents=True, exist_ok=True)
            shutil.copyfile(source_path, destination)
            copied.append(relative_path)
        return copied

    def ensure_demo_users(self):
        user_model = get_user_model()
        users = []
        for data in DEMO_USERS:
            user, created = user_model.objects.get_or_create(
                email=data["email"],
                defaults={"nickname": data["nickname"]},
            )
            fields_to_update = []
            if user.nickname != data["nickname"]:
                user.nickname = data["nickname"]
                fields_to_update.append("nickname")
            if created or not user.has_usable_password():
                user.set_unusable_password()
                fields_to_update.append("password")
            if fields_to_update:
                user.save(update_fields=fields_to_update)
            UserProfile.objects.get_or_create(user=user)
            users.append(user)
        return users

    def create_demo_reviews(self, demo_users, libraries, books, programs, tags_by_code):
        created_reviews = []
        book_index = 0
        program_index = 0
        for index, blueprint in enumerate(REVIEW_BLUEPRINTS):
            author = demo_users[index % len(demo_users)]
            program = None
            library = libraries[index]
            if blueprint.get("program"):
                program = programs[program_index % len(programs)]
                program_index += 1
                library = program.library

            review = UserReview.objects.create(
                user=author,
                library=library,
                content=blueprint["content"],
            )
            for tag_code in blueprint["tag_codes"]:
                ReviewTag.objects.create(review=review, tag=tags_by_code[tag_code])

            if blueprint.get("book"):
                book = books[book_index % len(books)]
                book_index += 1
                ReviewBookReference.objects.create(review=review, book=book, display_order=0)

            if program:
                ReviewProgramReference.objects.create(review=review, program=program, display_order=0)

            if blueprint.get("image"):
                UserReviewImage.objects.create(
                    review=review,
                    image=blueprint["image"],
                    alt_text=blueprint["alt_text"],
                    display_order=0,
                )
            created_reviews.append(review)

        # Give the primary demo account liked-review/dashboard data without liking its own reviews.
        liker = demo_users[0]
        for review in [review for review in created_reviews if review.user_id != liker.id][:3]:
            UserReviewLike.objects.create(user=liker, review=review)
            review.like_count = review.likes.count()
            review.save(update_fields=["like_count", "updated_at"])

        return created_reviews

    def print_summary(self, counts, missing_before, deleted_counts, copied_images, created_reviews, orphan_files):
        self.stdout.write("review data counts:")
        for key, value in counts.items():
            self.stdout.write(f"- {key}: {value}")
        self.stdout.write(f"- missing review image files before reset: {len(missing_before)}")
        for image_path in missing_before:
            self.stdout.write(f"  - {image_path}")
        if deleted_counts:
            self.stdout.write("deleted rows by model:")
            for model_name, count in sorted(deleted_counts.items()):
                self.stdout.write(f"- {model_name}: {count}")
        if copied_images:
            self.stdout.write("copied demo media files:")
            for image_path in copied_images:
                self.stdout.write(f"- {image_path}")
        if created_reviews:
            self.stdout.write(f"created demo reviews: {len(created_reviews)}")
            for review in created_reviews:
                self.stdout.write(f"- id={review.id} library={review.library_id} user={review.user_id}")
        if orphan_files:
            self.stdout.write("orphan review media files left in place:")
            for image_path in orphan_files:
                self.stdout.write(f"- {image_path}")
        else:
            self.stdout.write("orphan review media files left in place: none")
