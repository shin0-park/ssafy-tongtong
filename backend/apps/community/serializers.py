from django.db import transaction
from rest_framework import serializers

from apps.books.models import Book
from apps.libraries.models import Library
from apps.programs.models import Program
from apps.tags.models import Tag, TagSemanticKind

from .models import (
    ReviewBookReference,
    ReviewModerationStatus,
    ReviewProgramReference,
    ReviewTag,
    UserReview,
)


class ReviewLibrarySummarySerializer(serializers.Serializer):
    id = serializers.IntegerField()
    name = serializers.CharField()
    sigungu = serializers.CharField()


class ReviewUserSummarySerializer(serializers.Serializer):
    id = serializers.IntegerField()
    nickname = serializers.CharField()


class ReviewTagSummarySerializer(serializers.Serializer):
    id = serializers.IntegerField(source="tag.id")
    code = serializers.CharField(source="tag.code")
    label = serializers.CharField(source="tag.label")
    review_label = serializers.CharField(source="tag.review_label")


class ReviewImageSummarySerializer(serializers.Serializer):
    id = serializers.IntegerField()
    url = serializers.SerializerMethodField()
    alt_text = serializers.CharField()

    def get_url(self, obj):
        try:
            return obj.image.url
        except ValueError:
            return ""


class ReviewBookSummarySerializer(serializers.Serializer):
    id = serializers.IntegerField(source="book.id")
    isbn13 = serializers.CharField(source="book.isbn13")
    title = serializers.CharField(source="book.title")
    authors_text = serializers.CharField(source="book.authors_text")
    cover_image_url = serializers.CharField(source="book.cover_image_url")


class ReviewProgramSummarySerializer(serializers.Serializer):
    id = serializers.IntegerField(source="program.id")
    title = serializers.CharField(source="program.title")
    library_name = serializers.CharField(source="program.library.name")
    operation_start_date = serializers.DateField(source="program.operation_start_date")
    operation_end_date = serializers.DateField(source="program.operation_end_date")


class UserReviewSerializer(serializers.ModelSerializer):
    library = ReviewLibrarySummarySerializer(read_only=True)
    user = ReviewUserSummarySerializer(read_only=True)
    tags = serializers.SerializerMethodField()
    images = serializers.SerializerMethodField()
    related_books = serializers.SerializerMethodField()
    related_programs = serializers.SerializerMethodField()

    class Meta:
        model = UserReview
        fields = (
            "id",
            "library",
            "user",
            "content",
            "view_count",
            "like_count",
            "created_at",
            "updated_at",
            "tags",
            "images",
            "related_books",
            "related_programs",
        )

    def get_tags(self, obj):
        tag_links = getattr(obj, "prefetched_tag_links", None)
        if tag_links is None:
            tag_links = obj.tag_links.select_related("tag")
        return ReviewTagSummarySerializer(tag_links, many=True).data

    def get_images(self, obj):
        images = getattr(obj, "prefetched_images", None)
        if images is None:
            images = obj.images.order_by("display_order", "id")
        return ReviewImageSummarySerializer(images, many=True).data

    def get_related_books(self, obj):
        book_references = getattr(obj, "prefetched_book_references", None)
        if book_references is None:
            book_references = obj.book_references.select_related("book").order_by("display_order", "id")
        return ReviewBookSummarySerializer(book_references[:5], many=True).data

    def get_related_programs(self, obj):
        program_references = getattr(obj, "prefetched_program_references", None)
        if program_references is None:
            program_references = obj.program_references.select_related("program__library").order_by("display_order", "id")
        return ReviewProgramSummarySerializer(program_references[:5], many=True).data


class UserReviewWriteSerializer(serializers.Serializer):
    library_id = serializers.IntegerField(required=False)
    content = serializers.CharField(required=False, allow_blank=False, trim_whitespace=True)
    tag_codes = serializers.ListField(
        child=serializers.CharField(),
        required=False,
        allow_empty=True,
    )
    book_ids = serializers.ListField(
        child=serializers.IntegerField(),
        required=False,
        allow_empty=True,
    )
    program_ids = serializers.ListField(
        child=serializers.IntegerField(),
        required=False,
        allow_empty=True,
    )

    def validate(self, attrs):
        is_create = self.instance is None

        if is_create and "library_id" not in attrs:
            raise serializers.ValidationError({"library_id": "This field is required."})
        if is_create and "content" not in attrs:
            raise serializers.ValidationError({"content": "This field is required."})
        if is_create and "tag_codes" not in attrs:
            raise serializers.ValidationError({"tag_codes": "This field is required."})

        library = self.instance.library if self.instance else None
        if "library_id" in attrs:
            try:
                library = Library.objects.get(pk=attrs["library_id"], is_active=True)
            except Library.DoesNotExist:
                raise serializers.ValidationError({"library_id": "Library does not exist."})
            attrs["library"] = library

        if "content" in attrs:
            content = attrs["content"].strip()
            if not content:
                raise serializers.ValidationError({"content": "Review content is required."})
            if len(content) > 200:
                raise serializers.ValidationError({"content": "Review content must be 200 characters or fewer."})
            attrs["content"] = content

        if "tag_codes" in attrs:
            tag_codes = self.deduplicate(attrs["tag_codes"])
            if len(tag_codes) < 1:
                raise serializers.ValidationError({"tag_codes": "Select at least one review tag."})
            if len(tag_codes) > 5:
                raise serializers.ValidationError({"tag_codes": "Select no more than five review tags."})

            tags = list(
                Tag.objects.filter(
                    code__in=tag_codes,
                    is_review_selectable=True,
                    is_active=True,
                    semantic_kind=TagSemanticKind.EXPERIENCE,
                )
            )
            found_codes = {tag.code for tag in tags}
            invalid_codes = [code for code in tag_codes if code not in found_codes]
            if invalid_codes:
                raise serializers.ValidationError({"tag_codes": "Invalid review tag code."})
            attrs["tags"] = sorted(tags, key=lambda tag: tag_codes.index(tag.code))

        if "book_ids" in attrs:
            book_ids = self.deduplicate(attrs["book_ids"])
            books = list(Book.objects.filter(id__in=book_ids, is_active=True))
            found_ids = {book.id for book in books}
            invalid_ids = [book_id for book_id in book_ids if book_id not in found_ids]
            if invalid_ids:
                raise serializers.ValidationError({"book_ids": "Invalid book id."})
            attrs["books"] = sorted(books, key=lambda book: book_ids.index(book.id))

        if "program_ids" in attrs:
            program_ids = self.deduplicate(attrs["program_ids"])
            programs = list(
                Program.objects.filter(
                    id__in=program_ids,
                    is_visible=True,
                    deleted_at__isnull=True,
                )
            )
            found_ids = {program.id for program in programs}
            invalid_ids = [program_id for program_id in program_ids if program_id not in found_ids]
            if invalid_ids:
                raise serializers.ValidationError({"program_ids": "Invalid program id."})
            if library and any(program.library_id != library.id for program in programs):
                raise serializers.ValidationError({"program_ids": "Related programs must belong to the review library."})
            attrs["programs"] = sorted(programs, key=lambda program: program_ids.index(program.id))

        return attrs

    @staticmethod
    def deduplicate(values):
        deduplicated = []
        seen = set()
        for value in values:
            if value in seen:
                continue
            seen.add(value)
            deduplicated.append(value)
        return deduplicated

    @transaction.atomic
    def create(self, validated_data):
        review = UserReview.objects.create(
            user=self.context["request"].user,
            library=validated_data["library"],
            content=validated_data["content"],
            moderation_status=ReviewModerationStatus.VISIBLE,
        )
        self.replace_tags(review, validated_data["tags"])
        self.replace_book_references(review, validated_data.get("books", []))
        self.replace_program_references(review, validated_data.get("programs", []))
        return review

    @transaction.atomic
    def update(self, instance, validated_data):
        if "content" in validated_data:
            instance.content = validated_data["content"]
            instance.save(update_fields=["content", "updated_at"])

        if "tags" in validated_data:
            self.replace_tags(instance, validated_data["tags"])
        if "books" in validated_data:
            self.replace_book_references(instance, validated_data["books"])
        if "programs" in validated_data:
            self.replace_program_references(instance, validated_data["programs"])
        return instance

    @staticmethod
    def replace_tags(review, tags):
        ReviewTag.objects.filter(review=review).delete()
        ReviewTag.objects.bulk_create([ReviewTag(review=review, tag=tag) for tag in tags])

    @staticmethod
    def replace_book_references(review, books):
        ReviewBookReference.objects.filter(review=review).delete()
        ReviewBookReference.objects.bulk_create(
            [
                ReviewBookReference(review=review, book=book, display_order=index)
                for index, book in enumerate(books)
            ]
        )

    @staticmethod
    def replace_program_references(review, programs):
        ReviewProgramReference.objects.filter(review=review).delete()
        ReviewProgramReference.objects.bulk_create(
            [
                ReviewProgramReference(review=review, program=program, display_order=index)
                for index, program in enumerate(programs)
            ]
        )
