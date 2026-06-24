from rest_framework import serializers

from apps.books.serializers import BookListSerializer
from apps.libraries.serializers import LibraryListSerializer
from apps.myoutings.models import UserBookSave, UserLibrarySave, UserProgramSave
from apps.programs.serializers import ProgramListSerializer


class SavedBookSummarySerializer(BookListSerializer):
    class Meta(BookListSerializer.Meta):
        fields = (
            "id",
            "isbn13",
            "title",
            "authors_text",
            "publisher",
            "publication_year",
            "cover_image_url",
        )


class SavedProgramSummarySerializer(ProgramListSerializer):
    class Meta(ProgramListSerializer.Meta):
        fields = (
            "id",
            "title",
            "library",
            "category",
            "category_display",
            "target",
            "target_display",
            "operation_start_date",
            "operation_end_date",
            "operation_status",
            "operation_status_display",
        )


class UserLibrarySaveSerializer(serializers.ModelSerializer):
    library = LibraryListSerializer(read_only=True)

    class Meta:
        model = UserLibrarySave
        fields = ("id", "memo", "created_at", "updated_at", "library")


class UserBookSaveSerializer(serializers.ModelSerializer):
    book = SavedBookSummarySerializer(read_only=True)

    class Meta:
        model = UserBookSave
        fields = ("id", "memo", "created_at", "updated_at", "book")


class UserProgramSaveSerializer(serializers.ModelSerializer):
    program = SavedProgramSummarySerializer(read_only=True)

    class Meta:
        model = UserProgramSave
        fields = ("id", "memo", "created_at", "updated_at", "program")
