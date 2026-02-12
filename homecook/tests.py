from django.test import TestCase, Client
from django.contrib.auth.models import User
from django.urls import reverse
from accounts.models import UserProfile
from homecook.models import ChallengeSet, FoodImage, Receipt, Recipe, Journal


class TestHelper:
    """테스트 공통 헬퍼"""

    @staticmethod
    def create_user(username='testuser', password='testpass123!'):
        return User.objects.create_user(username=username, password=password)

    @staticmethod
    def create_challenge_set(user, title='테스트 챌린지'):
        return ChallengeSet.objects.create(user=user, title=title)

    @staticmethod
    def create_recipe(user, challenge_set=None, title='테스트 레시피', content='맛있는 요리'):
        return Recipe.objects.create(
            user=user, challenge_set=challenge_set,
            title=title, content=content,
        )

    @staticmethod
    def create_journal(user, challenge_set=None, title='테스트 기록',
                       content='오늘의 기록', visibility='private'):
        return Journal.objects.create(
            user=user, challenge_set=challenge_set,
            title=title, content=content, visibility=visibility,
        )


# ============================================================================
# 1. 챌린지 세트 생성 + 포인트 적립/차감 테스트
# ============================================================================

class ChallengeSetCreatePointsTest(TestCase):
    """챌린지 세트 생성 시 포인트 적립 테스트"""

    def setUp(self):
        self.client = Client()
        self.user = TestHelper.create_user()
        self.client.login(username='testuser', password='testpass123!')
        self.url = reverse('homecook:challenge_set_create')

    def test_create_challenge_set_awards_100_points(self):
        """챌린지 세트 생성 시 100P 적립"""
        self.client.post(self.url, {'set_title': '나의 첫 챌린지'})

        profile = UserProfile.objects.get(user=self.user)
        self.assertEqual(profile.points, 100)

    def test_create_multiple_sets_accumulates_points(self):
        """여러 세트 생성 시 포인트 누적"""
        self.client.post(self.url, {'set_title': '챌린지 1'})
        self.client.post(self.url, {'set_title': '챌린지 2'})
        self.client.post(self.url, {'set_title': '챌린지 3'})

        profile = UserProfile.objects.get(user=self.user)
        self.assertEqual(profile.points, 300)

    def test_create_set_creates_challenge_set_object(self):
        """챌린지 세트 DB 객체 생성 확인"""
        self.client.post(self.url, {'set_title': '새 챌린지'})

        self.assertEqual(ChallengeSet.objects.filter(user=self.user).count(), 1)
        cs = ChallengeSet.objects.get(user=self.user)
        self.assertEqual(cs.title, '새 챌린지')

    def test_create_set_redirects_to_my_challenge(self):
        """생성 후 my_challenge 페이지로 리다이렉트"""
        response = self.client.post(self.url, {'set_title': '새 챌린지'})
        self.assertRedirects(response, reverse('homecook:my_challenge'))

    def test_create_set_without_title_fails(self):
        """제목 없이 생성 시 실패"""
        self.client.post(self.url, {'set_title': ''})
        self.assertEqual(ChallengeSet.objects.count(), 0)

    def test_create_set_with_recipe(self):
        """레시피 포함 챌린지 세트 생성"""
        self.client.post(self.url, {
            'set_title': '레시피 챌린지',
            'recipe_title': '김치찌개',
            'recipe_content': '맛있는 김치찌개 레시피',
        })

        cs = ChallengeSet.objects.get(user=self.user)
        self.assertTrue(hasattr(cs, 'recipe'))
        self.assertEqual(cs.recipe.title, '김치찌개')

    def test_create_set_with_journal(self):
        """기록장 포함 챌린지 세트 생성"""
        self.client.post(self.url, {
            'set_title': '기록 챌린지',
            'journal_title': '오늘의 기록',
            'journal_content': '요리가 즐거웠다',
            'journal_visibility': 'public',
        })

        cs = ChallengeSet.objects.get(user=self.user)
        self.assertTrue(hasattr(cs, 'journal'))
        self.assertEqual(cs.journal.visibility, 'public')

    def test_create_set_requires_login(self):
        """비로그인 시 로그인 페이지로 리다이렉트"""
        self.client.logout()
        response = self.client.post(self.url, {'set_title': '테스트'})
        self.assertEqual(response.status_code, 302)
        self.assertIn('/accounts/login/', response.url)

    def test_recipe_title_without_content_fails(self):
        """레시피 제목만 있고 내용 없으면 유효성 검사 실패"""
        self.client.post(self.url, {
            'set_title': '챌린지',
            'recipe_title': '김치찌개',
            'recipe_content': '',
        })
        # 레시피가 생성되지 않아야 함
        self.assertEqual(Recipe.objects.count(), 0)


class ChallengeSetDeletePointsTest(TestCase):
    """챌린지 세트 삭제 테스트"""

    def setUp(self):
        self.client = Client()
        self.user = TestHelper.create_user()
        self.client.login(username='testuser', password='testpass123!')
        # 챌린지 세트 생성 (100P 적립됨)
        self.client.post(
            reverse('homecook:challenge_set_create'),
            {'set_title': '삭제 테스트용'},
        )
        self.challenge_set = ChallengeSet.objects.get(user=self.user)

    def test_delete_set_keeps_points(self):
        """챌린지 세트 삭제 시 포인트 변화 없음"""
        profile = UserProfile.objects.get(user=self.user)
        points_before = profile.points

        url = reverse('homecook:challenge_set_delete', kwargs={'pk': self.challenge_set.pk})
        self.client.post(url)

        profile.refresh_from_db()
        self.assertEqual(profile.points, points_before)

    def test_delete_set_removes_from_db(self):
        """삭제 후 DB에서 제거됨"""
        url = reverse('homecook:challenge_set_delete', kwargs={'pk': self.challenge_set.pk})
        self.client.post(url)

        self.assertEqual(ChallengeSet.objects.filter(pk=self.challenge_set.pk).count(), 0)

    def test_other_user_cannot_delete(self):
        """다른 사용자의 챌린지 세트 삭제 불가"""
        other_user = TestHelper.create_user(username='otheruser')
        self.client.login(username='otheruser', password='testpass123!')

        url = reverse('homecook:challenge_set_delete', kwargs={'pk': self.challenge_set.pk})
        response = self.client.post(url)
        self.assertEqual(response.status_code, 404)


# ============================================================================
# 3. 레시피 좋아요 토글 테스트
# ============================================================================

class RecipeLikeToggleTest(TestCase):
    """레시피 좋아요 토글 테스트"""

    def setUp(self):
        self.client = Client()
        self.user = TestHelper.create_user()
        self.other_user = TestHelper.create_user(username='other')
        self.recipe = TestHelper.create_recipe(user=self.user)
        self.url = reverse('homecook:recipe_like_toggle', kwargs={'pk': self.recipe.pk})

    def test_like_adds_user(self):
        """좋아요 누르면 likes에 추가"""
        self.client.login(username='testuser', password='testpass123!')
        response = self.client.post(self.url)

        data = response.json()
        self.assertTrue(data['liked'])
        self.assertEqual(data['total_likes'], 1)

    def test_unlike_removes_user(self):
        """다시 누르면 좋아요 취소"""
        self.client.login(username='testuser', password='testpass123!')
        self.client.post(self.url)  # 좋아요
        response = self.client.post(self.url)  # 취소

        data = response.json()
        self.assertFalse(data['liked'])
        self.assertEqual(data['total_likes'], 0)

    def test_multiple_users_like(self):
        """여러 사용자가 좋아요 가능"""
        self.client.login(username='testuser', password='testpass123!')
        self.client.post(self.url)

        self.client.login(username='other', password='testpass123!')
        response = self.client.post(self.url)

        data = response.json()
        self.assertEqual(data['total_likes'], 2)

    def test_returns_json_response(self):
        """JSON 응답 반환 확인"""
        self.client.login(username='testuser', password='testpass123!')
        response = self.client.post(self.url)

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response['Content-Type'], 'application/json')
        data = response.json()
        self.assertIn('liked', data)
        self.assertIn('total_likes', data)

    def test_get_method_not_allowed(self):
        """GET 요청 불가 (POST만 허용)"""
        self.client.login(username='testuser', password='testpass123!')
        response = self.client.get(self.url)
        self.assertEqual(response.status_code, 405)

    def test_anonymous_user_redirected(self):
        """비로그인 사용자 리다이렉트"""
        response = self.client.post(self.url)
        self.assertEqual(response.status_code, 302)
        self.assertIn('/accounts/login/', response.url)

    def test_like_nonexistent_recipe_returns_404(self):
        """존재하지 않는 레시피 좋아요 시 404"""
        self.client.login(username='testuser', password='testpass123!')
        url = reverse('homecook:recipe_like_toggle', kwargs={'pk': 9999})
        response = self.client.post(url)
        self.assertEqual(response.status_code, 404)


# ============================================================================
# 4. Journal 비공개 접근 제어 테스트
# ============================================================================

class JournalVisibilityTest(TestCase):
    """기록장 공개/비공개 접근 제어 테스트"""

    def setUp(self):
        self.client = Client()
        self.owner = TestHelper.create_user(username='owner')
        self.other_user = TestHelper.create_user(username='viewer')

        self.public_journal = TestHelper.create_journal(
            user=self.owner, title='공개 기록', visibility='public',
        )
        self.private_journal = TestHelper.create_journal(
            user=self.owner, title='비공개 기록', visibility='private',
        )

    def test_owner_can_view_public_journal(self):
        """작성자 본인은 공개 기록 조회 가능"""
        self.client.login(username='owner', password='testpass123!')
        url = reverse('homecook:journal_detail', kwargs={'pk': self.public_journal.pk})
        response = self.client.get(url)
        self.assertEqual(response.status_code, 200)

    def test_owner_can_view_private_journal(self):
        """작성자 본인은 비공개 기록 조회 가능"""
        self.client.login(username='owner', password='testpass123!')
        url = reverse('homecook:journal_detail', kwargs={'pk': self.private_journal.pk})
        response = self.client.get(url)
        self.assertEqual(response.status_code, 200)

    def test_other_user_can_view_public_journal(self):
        """다른 사용자는 공개 기록 조회 가능"""
        self.client.login(username='viewer', password='testpass123!')
        url = reverse('homecook:journal_detail', kwargs={'pk': self.public_journal.pk})
        response = self.client.get(url)
        self.assertEqual(response.status_code, 200)

    def test_other_user_cannot_view_private_journal(self):
        """다른 사용자는 비공개 기록 조회 불가 (404)"""
        self.client.login(username='viewer', password='testpass123!')
        url = reverse('homecook:journal_detail', kwargs={'pk': self.private_journal.pk})
        response = self.client.get(url)
        self.assertEqual(response.status_code, 404)

    def test_anonymous_can_view_public_journal(self):
        """비로그인 사용자도 공개 기록 조회 가능"""
        url = reverse('homecook:journal_detail', kwargs={'pk': self.public_journal.pk})
        response = self.client.get(url)
        self.assertEqual(response.status_code, 200)

    def test_anonymous_cannot_view_private_journal(self):
        """비로그인 사용자는 비공개 기록 조회 불가 (404)"""
        url = reverse('homecook:journal_detail', kwargs={'pk': self.private_journal.pk})
        response = self.client.get(url)
        self.assertEqual(response.status_code, 404)

    def test_journal_default_visibility_is_private(self):
        """기록장 기본 공개 설정은 비공개"""
        journal = Journal.objects.create(
            user=self.owner, title='기본값 테스트', content='내용',
        )
        self.assertEqual(journal.visibility, 'private')

    def test_journal_visibility_display(self):
        """공개 설정 표시값 확인"""
        self.assertEqual(self.public_journal.get_visibility_display(), '공개')
        self.assertEqual(self.private_journal.get_visibility_display(), '비공개')

