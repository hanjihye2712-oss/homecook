from decimal import Decimal
from django.test import TestCase, Client
from django.contrib.auth.models import User
from django.urls import reverse
from django.utils import timezone
from accounts.models import UserProfile
from information.models import Transaction


class TransactionTestHelper:
    """거래내역 테스트 공통 헬퍼"""

    @staticmethod
    def create_user(username='testuser', password='testpass123!'):
        return User.objects.create_user(username=username, password=password)

    @staticmethod
    def create_transaction(user, transaction_type='deposit', amount=10000,
                           category='salary', description='테스트 거래'):
        return Transaction.objects.create(
            user=user,
            transaction_type=transaction_type,
            amount=Decimal(str(amount)),
            category=category,
            description=description,
            transaction_date=timezone.now(),
        )


# ============================================================================
# 2. 포인트 → 서울페이 이체 테스트
# ============================================================================

class TransferToSeoulpayTest(TestCase):
    """포인트 → 서울페이 이체 테스트"""

    def setUp(self):
        self.client = Client()
        self.user = TransactionTestHelper.create_user()
        self.client.login(username='testuser', password='testpass123!')
        self.profile = UserProfile.objects.create(user=self.user, points=500)
        self.url = reverse('information:transfer_to_seoulpay')

    def test_transfer_success(self):
        """정상 이체: 포인트 차감 + Transaction 생성"""
        response = self.client.post(self.url, {'amount': '200'})

        self.profile.refresh_from_db()
        self.assertEqual(self.profile.points, 300)

        tx = Transaction.objects.get(user=self.user)
        self.assertEqual(tx.transaction_type, Transaction.SEOULPAY)
        self.assertEqual(tx.amount, Decimal('200'))
        self.assertEqual(tx.category, Transaction.HEALTH_POINT)

    def test_transfer_redirects_to_dashboard(self):
        """이체 후 통합 대시보드로 리다이렉트"""
        response = self.client.post(self.url, {'amount': '100'})
        self.assertRedirects(response, reverse('information:integrated_dashboard'))

    def test_transfer_insufficient_points(self):
        """잔액 부족 시 이체 실패"""
        self.client.post(self.url, {'amount': '999'})

        self.profile.refresh_from_db()
        self.assertEqual(self.profile.points, 500)  # 변동 없음
        self.assertEqual(Transaction.objects.count(), 0)

    def test_transfer_zero_amount(self):
        """금액 0 이체 시 실패"""
        self.client.post(self.url, {'amount': '0'})

        self.profile.refresh_from_db()
        self.assertEqual(self.profile.points, 500)
        self.assertEqual(Transaction.objects.count(), 0)

    def test_transfer_negative_amount(self):
        """음수 금액 이체 시 실패"""
        self.client.post(self.url, {'amount': '-100'})

        self.profile.refresh_from_db()
        self.assertEqual(self.profile.points, 500)
        self.assertEqual(Transaction.objects.count(), 0)

    def test_transfer_invalid_amount(self):
        """잘못된 형식 금액 이체 시 실패"""
        self.client.post(self.url, {'amount': 'abc'})

        self.profile.refresh_from_db()
        self.assertEqual(self.profile.points, 500)
        self.assertEqual(Transaction.objects.count(), 0)

    def test_transfer_records_balance_after(self):
        """이체 후 잔액이 Transaction에 기록됨"""
        self.client.post(self.url, {'amount': '200'})

        tx = Transaction.objects.get(user=self.user)
        self.assertEqual(tx.balance_after, Decimal('300'))

    def test_transfer_requires_login(self):
        """비로그인 사용자 리다이렉트"""
        self.client.logout()
        response = self.client.post(self.url, {'amount': '100'})
        self.assertEqual(response.status_code, 302)
        self.assertIn('/accounts/login/', response.url)

    def test_transfer_get_method_not_allowed(self):
        """GET 요청 불가 (POST만 허용)"""
        response = self.client.get(self.url)
        self.assertEqual(response.status_code, 405)

    def test_transfer_all_points(self):
        """전체 포인트 이체"""
        self.client.post(self.url, {'amount': '500'})

        self.profile.refresh_from_db()
        self.assertEqual(self.profile.points, 0)


# ============================================================================
# 5. 거래내역 CRUD + 대시보드 통계 테스트
# ============================================================================

class TransactionCRUDTest(TestCase):
    """거래내역 CRUD 테스트"""

    def setUp(self):
        self.client = Client()
        self.user = TransactionTestHelper.create_user()
        self.other_user = TransactionTestHelper.create_user(username='other')
        self.client.login(username='testuser', password='testpass123!')

    def test_create_transaction(self):
        """거래내역 생성"""
        url = reverse('information:transaction_create')
        response = self.client.post(url, {
            'transaction_type': 'deposit',
            'amount': '50000',
            'category': 'salary',
            'description': '월급',
            'transaction_date': '2026-02-10T09:00',
        })

        self.assertEqual(Transaction.objects.filter(user=self.user).count(), 1)
        tx = Transaction.objects.get(user=self.user)
        self.assertEqual(tx.amount, Decimal('50000'))
        self.assertEqual(tx.transaction_type, 'deposit')

    def test_create_transaction_redirects(self):
        """생성 후 대시보드로 리다이렉트"""
        url = reverse('information:transaction_create')
        response = self.client.post(url, {
            'transaction_type': 'deposit',
            'amount': '10000',
            'category': 'salary',
            'transaction_date': '2026-02-10T09:00',
        })
        self.assertRedirects(response, reverse('information:integrated_dashboard'))

    def test_view_own_transaction(self):
        """본인 거래내역 상세 조회"""
        tx = TransactionTestHelper.create_transaction(self.user)
        url = reverse('information:transaction_detail', kwargs={'pk': tx.pk})
        response = self.client.get(url)
        self.assertEqual(response.status_code, 200)

    def test_cannot_view_others_transaction(self):
        """타인 거래내역 조회 불가"""
        tx = TransactionTestHelper.create_transaction(self.other_user)
        url = reverse('information:transaction_detail', kwargs={'pk': tx.pk})
        response = self.client.get(url)
        self.assertEqual(response.status_code, 403)

    def test_update_own_transaction(self):
        """본인 거래내역 수정"""
        tx = TransactionTestHelper.create_transaction(self.user)
        url = reverse('information:transaction_update', kwargs={'pk': tx.pk})
        response = self.client.post(url, {
            'transaction_type': 'withdrawal',
            'amount': '20000',
            'category': 'food',
            'description': '외식',
            'transaction_date': '2026-02-10T12:00',
        })

        tx.refresh_from_db()
        self.assertEqual(tx.amount, Decimal('20000'))
        self.assertEqual(tx.transaction_type, 'withdrawal')

    def test_cannot_update_others_transaction(self):
        """타인 거래내역 수정 불가"""
        tx = TransactionTestHelper.create_transaction(self.other_user)
        url = reverse('information:transaction_update', kwargs={'pk': tx.pk})
        response = self.client.post(url, {
            'transaction_type': 'deposit',
            'amount': '99999',
            'category': 'salary',
            'transaction_date': '2026-02-10T09:00',
        })
        self.assertEqual(response.status_code, 403)

    def test_delete_own_transaction(self):
        """본인 거래내역 삭제"""
        tx = TransactionTestHelper.create_transaction(self.user)
        url = reverse('information:transaction_delete', kwargs={'pk': tx.pk})
        response = self.client.post(url)

        self.assertEqual(Transaction.objects.filter(pk=tx.pk).count(), 0)

    def test_cannot_delete_others_transaction(self):
        """타인 거래내역 삭제 불가"""
        tx = TransactionTestHelper.create_transaction(self.other_user)
        url = reverse('information:transaction_delete', kwargs={'pk': tx.pk})
        response = self.client.post(url)
        self.assertEqual(response.status_code, 403)

    def test_transaction_list_requires_login(self):
        """거래내역 목록 로그인 필수"""
        self.client.logout()
        url = reverse('information:transaction_list')
        response = self.client.get(url)
        self.assertEqual(response.status_code, 302)
        self.assertIn('/accounts/login/', response.url)

    def test_transaction_list_shows_only_own(self):
        """거래내역 목록에 본인 거래만 표시"""
        TransactionTestHelper.create_transaction(self.user, description='내 거래')
        TransactionTestHelper.create_transaction(self.other_user, description='타인 거래')

        url = reverse('information:transaction_list')
        response = self.client.get(url)

        self.assertContains(response, '내 거래')
        self.assertNotContains(response, '타인 거래')


class TransactionModelTest(TestCase):
    """거래내역 모델 메서드 테스트"""

    def setUp(self):
        self.user = TransactionTestHelper.create_user()

    def test_is_income_deposit(self):
        """입금은 수입"""
        tx = TransactionTestHelper.create_transaction(self.user, transaction_type='deposit')
        self.assertTrue(tx.is_income())

    def test_is_income_withdrawal(self):
        """출금은 수입 아님"""
        tx = TransactionTestHelper.create_transaction(self.user, transaction_type='withdrawal')
        self.assertFalse(tx.is_income())

    def test_is_expense_withdrawal(self):
        """출금은 지출"""
        tx = TransactionTestHelper.create_transaction(
            self.user, transaction_type='withdrawal', category='food',
        )
        self.assertTrue(tx.is_expense())

    def test_is_expense_seoulpay(self):
        """서울페이도 지출 (health_point 제외)"""
        tx = TransactionTestHelper.create_transaction(
            self.user, transaction_type='seoulpay', category='food',
        )
        self.assertTrue(tx.is_expense())

    def test_health_point_seoulpay_not_expense(self):
        """서울페이 + health_point 카테고리는 지출이 아님"""
        tx = TransactionTestHelper.create_transaction(
            self.user, transaction_type='seoulpay', category='health_point',
        )
        self.assertFalse(tx.is_expense())

    def test_get_amount_display(self):
        """금액 표시 형식"""
        tx = TransactionTestHelper.create_transaction(self.user, amount=50000)
        self.assertEqual(tx.get_amount_display(), '50,000원')

    def test_clean_zero_amount_raises(self):
        """금액 0 유효성 검사 실패"""
        tx = Transaction(
            user=self.user, transaction_type='deposit',
            amount=Decimal('0'), category='salary',
            transaction_date=timezone.now(),
        )
        from django.core.exceptions import ValidationError
        with self.assertRaises(ValidationError):
            tx.clean()


class DashboardStatsTest(TestCase):
    """대시보드 통계 정합성 테스트"""

    def setUp(self):
        self.client = Client()
        self.user = TransactionTestHelper.create_user()
        self.client.login(username='testuser', password='testpass123!')

        # 이번 달 거래 데이터 생성
        now = timezone.now()
        Transaction.objects.create(
            user=self.user, transaction_type='deposit',
            amount=Decimal('100000'), category='salary',
            description='월급', transaction_date=now,
        )
        Transaction.objects.create(
            user=self.user, transaction_type='withdrawal',
            amount=Decimal('30000'), category='food',
            description='식비', transaction_date=now,
        )
        Transaction.objects.create(
            user=self.user, transaction_type='withdrawal',
            amount=Decimal('20000'), category='transport',
            description='교통비', transaction_date=now,
        )

    def test_dashboard_accessible(self):
        """대시보드 페이지 접근 가능"""
        url = reverse('information:integrated_dashboard')
        response = self.client.get(url)
        self.assertEqual(response.status_code, 200)

    def test_dashboard_shows_income(self):
        """대시보드에 수입 합계 표시"""
        url = reverse('information:integrated_dashboard')
        response = self.client.get(url)
        self.assertEqual(response.context['total_income'], Decimal('100000'))

    def test_dashboard_shows_expense(self):
        """대시보드에 지출 합계 표시"""
        url = reverse('information:integrated_dashboard')
        response = self.client.get(url)
        self.assertEqual(response.context['total_expense'], Decimal('50000'))

    def test_dashboard_shows_balance(self):
        """대시보드에 수지 표시 (수입 - 지출)"""
        url = reverse('information:integrated_dashboard')
        response = self.client.get(url)
        self.assertEqual(response.context['net_balance'], Decimal('50000'))

    def test_dashboard_transaction_count(self):
        """대시보드에 거래 건수 표시"""
        url = reverse('information:integrated_dashboard')
        response = self.client.get(url)
        self.assertEqual(response.context['transaction_count'], 3)

    def test_dashboard_requires_login(self):
        """대시보드 로그인 필수"""
        self.client.logout()
        url = reverse('information:integrated_dashboard')
        response = self.client.get(url)
        self.assertEqual(response.status_code, 302)
        self.assertIn('/accounts/login/', response.url)

    def test_dashboard_no_data(self):
        """거래 없는 사용자 대시보드 (오류 없이 표시)"""
        other = TransactionTestHelper.create_user(username='empty')
        self.client.login(username='empty', password='testpass123!')

        url = reverse('information:integrated_dashboard')
        response = self.client.get(url)
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.context['total_income'], Decimal('0'))
