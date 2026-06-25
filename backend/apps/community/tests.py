from unittest.mock import patch

from django.contrib.auth import get_user_model
from django.test import TestCase
from rest_framework.test import APIClient

from apps.community.models import ReviewModerationStatus, UserReview, UserReviewComment
from apps.libraries.models import Library, LibraryType


class ReviewCommentAPITestCase(TestCase):
    def setUp(self):
        self.client = APIClient()
        self.user = get_user_model().objects.create_user(
            email="commenter@example.com",
            password="password",
            nickname="댓글러",
        )
        self.other_user = get_user_model().objects.create_user(
            email="other@example.com",
            password="password",
            nickname="다른사용자",
        )
        self.library = Library.objects.create(
            name="테스트도서관",
            normalized_name="테스트도서관",
            sido="부산광역시",
            sigungu="해운대구",
            library_type=LibraryType.PUBLIC,
            road_address="부산광역시 해운대구 테스트로 1",
            normalized_address="부산광역시 해운대구 테스트로 1",
        )
        self.review = UserReview.objects.create(
            user=self.user,
            library=self.library,
            content="조용하고 좋아요.",
            moderation_status=ReviewModerationStatus.VISIBLE,
        )

    def test_comment_list_and_detail_are_public(self):
        comment = UserReviewComment.objects.create(
            user=self.user,
            review=self.review,
            content="저도 좋았어요.",
        )

        list_response = self.client.get(f"/api/v1/reviews/{self.review.id}/comments/")
        self.assertEqual(list_response.status_code, 200)
        self.assertEqual(list_response.data["count"], 1)
        self.assertEqual(list_response.data["results"][0]["content"], "저도 좋았어요.")

        detail_response = self.client.get(
            f"/api/v1/reviews/{self.review.id}/comments/{comment.id}/"
        )
        self.assertEqual(detail_response.status_code, 200)
        self.assertEqual(detail_response.data["id"], comment.id)

    def test_authenticated_user_can_create_comment_without_preference_schedule(self):
        self.client.force_authenticate(self.other_user)

        with patch("apps.community.views.schedule_user_preference_pending") as schedule_mock:
            response = self.client.post(
                f"/api/v1/reviews/{self.review.id}/comments/",
                {"content": "좋은 정보 감사합니다."},
                format="json",
            )

        self.assertEqual(response.status_code, 201)
        self.assertEqual(response.data["content"], "좋은 정보 감사합니다.")
        self.assertEqual(UserReviewComment.objects.count(), 1)
        schedule_mock.assert_not_called()

    def test_comment_content_validation(self):
        self.client.force_authenticate(self.user)

        blank_response = self.client.post(
            f"/api/v1/reviews/{self.review.id}/comments/",
            {"content": "   "},
            format="json",
        )
        self.assertEqual(blank_response.status_code, 400)

        long_response = self.client.post(
            f"/api/v1/reviews/{self.review.id}/comments/",
            {"content": "가" * 201},
            format="json",
        )
        self.assertEqual(long_response.status_code, 400)

    def test_only_comment_owner_can_update_and_delete(self):
        comment = UserReviewComment.objects.create(
            user=self.user,
            review=self.review,
            content="처음 댓글",
        )

        self.client.force_authenticate(self.other_user)
        forbidden_response = self.client.patch(
            f"/api/v1/reviews/{self.review.id}/comments/{comment.id}/",
            {"content": "남의 댓글 수정"},
            format="json",
        )
        self.assertEqual(forbidden_response.status_code, 403)

        self.client.force_authenticate(self.user)
        update_response = self.client.patch(
            f"/api/v1/reviews/{self.review.id}/comments/{comment.id}/",
            {"content": "수정한 댓글"},
            format="json",
        )
        self.assertEqual(update_response.status_code, 200)
        self.assertEqual(update_response.data["content"], "수정한 댓글")

        delete_response = self.client.delete(
            f"/api/v1/reviews/{self.review.id}/comments/{comment.id}/"
        )
        self.assertEqual(delete_response.status_code, 204)
        self.assertFalse(UserReviewComment.objects.filter(pk=comment.id).exists())

    def test_review_comment_count_changes_after_comment_delete(self):
        comment = UserReviewComment.objects.create(
            user=self.user,
            review=self.review,
            content="댓글",
        )

        detail_response = self.client.get(f"/api/v1/reviews/{self.review.id}/")
        self.assertEqual(detail_response.status_code, 200)
        self.assertEqual(detail_response.data["comment_count"], 1)

        self.client.force_authenticate(self.user)
        self.client.delete(f"/api/v1/reviews/{self.review.id}/comments/{comment.id}/")

        detail_response = self.client.get(f"/api/v1/reviews/{self.review.id}/")
        self.assertEqual(detail_response.data["comment_count"], 0)

    def test_review_delete_cascades_comments(self):
        UserReviewComment.objects.create(
            user=self.user,
            review=self.review,
            content="삭제될 댓글",
        )

        self.review.delete()

        self.assertEqual(UserReviewComment.objects.count(), 0)

    def test_my_outings_comments_returns_comment_with_review(self):
        UserReviewComment.objects.create(
            user=self.other_user,
            review=self.review,
            content="내 댓글",
        )
        self.client.force_authenticate(self.other_user)

        response = self.client.get("/api/v1/my-outings/comments/")

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data["count"], 1)
        self.assertEqual(response.data["results"][0]["content"], "내 댓글")
        self.assertEqual(response.data["results"][0]["review"]["id"], self.review.id)
