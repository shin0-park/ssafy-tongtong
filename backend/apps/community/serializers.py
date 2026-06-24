from rest_framework import serializers

from .models import UserReview


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
