from django.shortcuts import get_object_or_404
from rest_framework import status
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from apps.books.models import Book
from apps.libraries.models import Library
from apps.myoutings.models import UserBookSave, UserLibrarySave, UserProgramSave
from apps.programs.models import Program


class BaseSaveAPIView(APIView):
    permission_classes = (IsAuthenticated,)
    target_type = None
    lookup_url_kwarg = None
    save_model = None
    save_field = None

    def get_target(self):
        raise NotImplementedError

    def get_response_target_id(self, target):
        return target.pk

    def build_response(self, target, saved):
        return {
            "saved": saved,
            "target_type": self.target_type,
            "target_id": self.get_response_target_id(target),
        }

    def post(self, request, *args, **kwargs):
        target = self.get_target()
        _, created = self.save_model.objects.get_or_create(
            user=request.user,
            **{self.save_field: target},
        )
        response_status = status.HTTP_201_CREATED if created else status.HTTP_200_OK
        return Response(self.build_response(target, True), status=response_status)

    def delete(self, request, *args, **kwargs):
        target = self.get_target()
        self.save_model.objects.filter(
            user=request.user,
            **{self.save_field: target},
        ).delete()
        return Response(self.build_response(target, False), status=status.HTTP_200_OK)


class LibrarySaveAPIView(BaseSaveAPIView):
    target_type = "library"
    lookup_url_kwarg = "library_id"
    save_model = UserLibrarySave
    save_field = "library"

    def get_target(self):
        return get_object_or_404(
            Library.objects.filter(is_active=True),
            pk=self.kwargs[self.lookup_url_kwarg],
        )


class BookSaveAPIView(BaseSaveAPIView):
    target_type = "book"
    lookup_url_kwarg = "isbn13"
    save_model = UserBookSave
    save_field = "book"

    def get_target(self):
        return get_object_or_404(
            Book.objects.filter(is_active=True),
            isbn13=self.kwargs[self.lookup_url_kwarg],
        )

    def get_response_target_id(self, target):
        return target.isbn13


class ProgramSaveAPIView(BaseSaveAPIView):
    target_type = "program"
    lookup_url_kwarg = "program_id"
    save_model = UserProgramSave
    save_field = "program"

    def get_target(self):
        return get_object_or_404(
            Program.objects.filter(is_visible=True, deleted_at__isnull=True),
            pk=self.kwargs[self.lookup_url_kwarg],
        )
