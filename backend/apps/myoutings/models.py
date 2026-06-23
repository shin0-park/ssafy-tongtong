from django.conf import settings
from django.db import models

from apps.common.models import TimeStampedModel


class UserLibrarySave(TimeStampedModel):
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="saved_libraries",
    )
    library = models.ForeignKey(
        "libraries.Library",
        on_delete=models.CASCADE,
        related_name="saved_by_users",
    )
    memo = models.CharField(max_length=300, blank=True)

    class Meta:
        constraints = [
            models.UniqueConstraint(fields=["user", "library"], name="uq_user_library_save")
        ]
        indexes = [
            models.Index(fields=["user", "-created_at"], name="idx_user_library_save_recent")
        ]

    def __str__(self):
        return f"{self.user_id}:{self.library_id}"


class UserBookSave(TimeStampedModel):
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="saved_books",
    )
    book = models.ForeignKey(
        "books.Book",
        on_delete=models.CASCADE,
        related_name="saved_by_users",
    )
    memo = models.CharField(max_length=300, blank=True)

    class Meta:
        constraints = [
            models.UniqueConstraint(fields=["user", "book"], name="uq_user_book_save")
        ]
        indexes = [
            models.Index(fields=["user", "-created_at"], name="idx_user_book_save_recent")
        ]

    def __str__(self):
        return f"{self.user_id}:{self.book_id}"


class UserProgramSave(TimeStampedModel):
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="saved_programs",
    )
    program = models.ForeignKey(
        "programs.Program",
        on_delete=models.CASCADE,
        related_name="saved_by_users",
    )
    memo = models.CharField(max_length=300, blank=True)

    class Meta:
        constraints = [
            models.UniqueConstraint(fields=["user", "program"], name="uq_user_program_save")
        ]
        indexes = [
            models.Index(fields=["user", "-created_at"], name="idx_user_program_save_recent")
        ]

    def __str__(self):
        return f"{self.user_id}:{self.program_id}"
