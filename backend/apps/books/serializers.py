from rest_framework import serializers

from django.utils import timezone

from .models import Book, PopularBookItem, PopularBookSnapshot


class BookTagSummarySerializer(serializers.Serializer):
    id = serializers.IntegerField(source="tag.id")
    code = serializers.CharField(source="tag.code")
    label = serializers.CharField(source="tag.label")


class BookListSerializer(serializers.ModelSerializer):
    class Meta:
        model = Book
        fields = (
            "id",
            "isbn13",
            "title",
            "authors_text",
            "publisher",
            "publication_year",
            "kdc_class_no",
            "kdc_class_name",
            "cover_image_url",
            "is_active",
        )


class BookDetailSerializer(BookListSerializer):
    tags = serializers.SerializerMethodField()

    class Meta(BookListSerializer.Meta):
        fields = BookListSerializer.Meta.fields + (
            "publication_date",
            "volume",
            "addition_symbol",
            "description",
            "source_detail_url",
            "provider_code",
            "metadata_fetched_at",
            "tags",
        )

    def get_tags(self, obj):
        tag_links = getattr(obj, "active_tag_links", None)
        if tag_links is None:
            tag_links = obj.tag_links.filter(is_active=True).select_related("tag")
        return BookTagSummarySerializer(tag_links, many=True).data


class PopularBookSnapshotSerializer(serializers.ModelSerializer):
    generated_at = serializers.DateTimeField(source="created_at")
    is_stale = serializers.SerializerMethodField()

    class Meta:
        model = PopularBookSnapshot
        fields = (
            "id",
            "provider_code",
            "scope_type",
            "region_code",
            "period_start",
            "period_end",
            "generated_at",
            "fetched_at",
            "fresh_until",
            "result_count",
            "is_stale",
        )

    def get_is_stale(self, obj):
        return bool(obj.fresh_until and obj.fresh_until < timezone.now())


class PopularBookItemSerializer(serializers.ModelSerializer):
    book = BookListSerializer(read_only=True)

    class Meta:
        model = PopularBookItem
        fields = (
            "rank",
            "loan_count",
            "book",
        )
