from django.views import generic
from django.contrib.auth.mixins import LoginRequiredMixin, UserPassesTestMixin
from django.urls import reverse_lazy
from django.contrib import messages
from django.db.models import Sum, Q, Count, Avg
from django.db.models.functions import TruncMonth, TruncDate
from django.utils import timezone
from django.core.exceptions import ObjectDoesNotExist
from datetime import timedelta, datetime
from decimal import Decimal
from collections import defaultdict
from .models import Transaction
from .forms import TransactionForm

from django.shortcuts import render, redirect
from django.contrib.auth.decorators import login_required
from django.views.decorators.http import require_POST
from accounts.models import UserProfile

# ============= UTILITY FUNCTIONS ============= #

def calculate_percentage(value, total):
    """백분율 계산 (0~100)

    Args:
        value: 계산할 값
        total: 전체 값

    Returns:
        float: 백분율 (0~100), 오류 시 0
    """
    if not total or total == 0:
        return 0

    try:
        percentage = (Decimal(str(value)) / Decimal(str(total))) * 100
        return min(float(percentage), 100)
    except (ValueError, TypeError, ZeroDivisionError):
        return 0


def get_month_range(months_back=1):
    """월별 날짜 범위 반환

    Args:
        months_back: 몇 개월 전까지 조회할지 (기본값: 1)

    Returns:
        tuple: (start_date, end_date)
    """
    end_date = timezone.now()
    start_date = end_date - timedelta(days=30 * months_back)
    return start_date, end_date


def get_current_month_start():
    """이번 달 시작일 반환

    Returns:
        datetime: 이번 달 1일 00:00:00
    """
    now = timezone.now()
    return now.replace(day=1, hour=0, minute=0, second=0, microsecond=0)


def calculate_transaction_stats(queryset, transaction_type_deposit,
                               transaction_type_withdrawal, transaction_type_transfer):
    """거래내역 통계 계산

    Args:
        queryset: Transaction queryset
        transaction_type_deposit: 입금 타입 상수
        transaction_type_withdrawal: 출금 타입 상수
        transaction_type_transfer: 이체 타입 상수

    Returns:
        dict: income, expense, balance 포함
    """
    # 수입 합계
    income = queryset.filter(
        transaction_type=transaction_type_deposit
    ).aggregate(total=Sum('amount'))['total'] or Decimal('0')

    # 지출 합계 (건강 포인트 전송 제외)
    expense = queryset.filter(
        transaction_type__in=[transaction_type_withdrawal, transaction_type_transfer]
    ).exclude(
        category='health_point'
    ).aggregate(total=Sum('amount'))['total'] or Decimal('0')

    return {
        'income': income,
        'expense': expense,
        'balance': income - expense,
    }


def validate_period_parameter(period_str, min_val=1, max_val=24, default=6):
    """기간 파라미터 검증

    Args:
        period_str: 검증할 기간 문자열
        min_val: 최소값 (기본값: 1)
        max_val: 최대값 (기본값: 24)
        default: 기본값 (기본값: 6)

    Returns:
        int: 검증된 기간 값
    """
    try:
        period = int(period_str)
        return min(max(period, min_val), max_val)
    except (ValueError, TypeError):
        return default


# ============= CONSTANTS ============= #
LOGIN_URL = '/accounts/login/'
SUCCESS_URL = reverse_lazy('information:integrated_dashboard')

# 메시지 템플릿
MSG_CREATE_SUCCESS = '{type} 거래내역이 등록되었습니다! (금액: {amount}원) 💰'
MSG_UPDATE_SUCCESS = '거래내역이 성공적으로 수정되었습니다! ✏️'
MSG_DELETE_SUCCESS = '거래내역이 성공적으로 삭제되었습니다! 🗑️'
MSG_FORM_ERROR = '거래내역 {action}에 실패했습니다. 입력 내용을 확인해주세요.'


# ============= BASE MIXINS =============
class TransactionFilterMixin:
    """거래내역 필터링 공통 기능

    검색, 카테고리, 거래유형 필터 적용
    """

    def _apply_filters(self, queryset):
        """검색 및 필터 적용

        Args:
            queryset: Transaction queryset

        Returns:
            필터가 적용된 queryset
        """
        # 검색 (Walrus 연산자)
        if search := self.request.GET.get('search'):
            queryset = queryset.filter(
                Q(description__icontains=search) | Q(memo__icontains=search)
            )

        # 카테고리 필터
        if category := self.request.GET.get('category'):
            queryset = queryset.filter(category=category)

        # 거래 유형 필터
        if trans_type := self.request.GET.get('type'):
            queryset = queryset.filter(transaction_type=trans_type)

        # 날짜 필터 (시작일)
        if start_date := self.request.GET.get('start_date'):
            try:
                start_datetime = datetime.strptime(start_date, '%Y-%m-%d')
                queryset = queryset.filter(transaction_date__gte=start_datetime)
            except ValueError:
                pass  # 잘못된 날짜 형식은 무시

        # 날짜 필터 (종료일)
        if end_date := self.request.GET.get('end_date'):
            try:
                end_datetime = datetime.strptime(end_date, '%Y-%m-%d')
                # 종료일의 23:59:59까지 포함
                end_datetime = end_datetime.replace(hour=23, minute=59, second=59)
                queryset = queryset.filter(transaction_date__lte=end_datetime)
            except ValueError:
                pass  # 잘못된 날짜 형식은 무시

        return queryset

    def _get_filter_context(self):
        """필터 상태 컨텍스트

        Returns:
            dict: 필터 상태 정보
        """
        return {
            'selected_category': self.request.GET.get('category', ''),
            'selected_type': self.request.GET.get('type', ''),
            'search_query': self.request.GET.get('search', ''),
            'start_date': self.request.GET.get('start_date', ''),
            'end_date': self.request.GET.get('end_date', ''),
            'categories': Transaction.CATEGORY_CHOICES,
            'transaction_types': Transaction.TRANSACTION_TYPE_CHOICES,
        }


class TransactionBaseMixin(LoginRequiredMixin):
    """거래내역 공통 설정"""
    model = Transaction
    login_url = LOGIN_URL
    success_url = SUCCESS_URL


class UserOwnerMixin(UserPassesTestMixin):
    """본인 소유 거래내역만 접근 허용"""
    
    def test_func(self):
        """권한 검증: 본인의 거래내역만 접근 가능"""
        try:
            return self.get_object().user == self.request.user
        except (ObjectDoesNotExist, AttributeError):
            return False


class FormMessageMixin:
    """폼 처리 메시지 공통화"""
    success_message = ''
    error_message = ''
    
    def form_valid(self, form):
        """폼 유효성 검사 성공 시 - 사용자 자동 설정"""
        # 사용자 설정 (중복 제거)
        if not form.instance.user_id:
            form.instance.user = self.request.user
        
        response = super().form_valid(form)
        
        if self.success_message:
            messages.success(self.request, self.success_message)
        
        return response
    
    def form_invalid(self, form):
        """폼 유효성 검사 실패 시"""
        if self.error_message:
            messages.error(self.request, self.error_message)
        return super().form_invalid(form)


class DateTimeInitialMixin:
    """거래 일시 초기값 설정 공통화"""
    
    def get_initial(self):
        """초기값: 거래 일시를 datetime-local 형식으로"""
        initial = super().get_initial()
        initial['transaction_date'] = self._get_formatted_datetime()
        return initial
    
    def _get_formatted_datetime(self):
        """datetime-local 형식으로 포맷된 날짜 반환"""
        try:
            # UpdateView: 기존 객체의 거래 일시
            obj = self.get_object()
            if obj.transaction_date:
                local_dt = timezone.localtime(obj.transaction_date)
                return local_dt.strftime('%Y-%m-%dT%H:%M')
        except (AttributeError, ObjectDoesNotExist):
            # CreateView 또는 예외 발생 시: 현재 시간
            pass
        
        return timezone.now().strftime('%Y-%m-%dT%H:%M')


# ============= LIST VIEW =============
class TransactionListView(TransactionBaseMixin, TransactionFilterMixin, generic.ListView):
    """거래내역 목록 페이지
    
    Features:
    - 사용자별 거래내역 필터링
    - 검색 기능 (description, memo)
    - 카테고리/유형 필터
    - 월별 통계 (수입/지출/수지)
    - 페이지네이션 (20개)
    """
    template_name = 'information/transaction_list.html'
    context_object_name = 'transactions'
    paginate_by = 20
    
    def get_queryset(self):
        """사용자 거래내역 + 검색/필터"""
        try:
            queryset = Transaction.objects.filter(user=self.request.user)
            queryset = self._apply_filters(queryset)
            return queryset
        except Exception:
            return Transaction.objects.none()
    
    
    def get_context_data(self, **kwargs):
        """컨텍스트 데이터 추가 (월별 통계 + 필터 상태)"""
        context = super().get_context_data(**kwargs)
        
        # 월별 통계 추가
        context.update(self._get_monthly_stats())
        
        # 필터 상태 추가
        context.update(self._get_filter_context())
        
        return context
    
    def _get_monthly_stats(self):
        """이번 달 수입/지출 통계 계산"""
        try:
            month_start = get_current_month_start()
            month_trans = Transaction.objects.filter(
                user=self.request.user,
                transaction_date__gte=month_start
            )

            stats = calculate_transaction_stats(
                month_trans,
                Transaction.DEPOSIT,
                Transaction.WITHDRAWAL,
                Transaction.SEOULPAY
            )

            return {
                'monthly_income': stats['income'],
                'monthly_expense': stats['expense'],
                'monthly_balance': stats['balance'],
            }
        except Exception:
            return {
                'monthly_income': Decimal('0'),
                'monthly_expense': Decimal('0'),
                'monthly_balance': Decimal('0'),
            }
    


# ============= DETAIL VIEW =============
class TransactionDetailView(TransactionBaseMixin, UserOwnerMixin, generic.DetailView):
    """거래내역 상세 조회
    
    Permission: 본인 거래내역만 조회 가능
    """
    template_name = 'information/transaction_detail.html'
    context_object_name = 'transaction'


# ============= CREATE VIEW =============
class TransactionCreateView(
    TransactionBaseMixin, 
    FormMessageMixin, 
    DateTimeInitialMixin, 
    generic.CreateView
):
    """거래내역 등록
    
    Features:
    - 자동으로 현재 사용자 설정
    - 현재 시간을 초기값으로 설정
    - 성공/실패 메시지 표시
    """
    form_class = TransactionForm
    template_name = 'information/transaction_form.html'
    error_message = MSG_FORM_ERROR.format(action='등록')
    
    def form_valid(self, form):
        """폼 유효성 검사 성공 시 - 동적 메시지 생성"""
        # 동적 성공 메시지 설정
        self.success_message = MSG_CREATE_SUCCESS.format(
            type=form.instance.get_transaction_type_display(),
            amount=f'{form.instance.amount:,.0f}'
        )
        
        return super().form_valid(form)


# ============= UPDATE VIEW =============
class TransactionUpdateView(
    TransactionBaseMixin, 
    UserOwnerMixin, 
    FormMessageMixin, 
    DateTimeInitialMixin, 
    generic.UpdateView
):
    """거래내역 수정
    
    Permission: 본인 거래내역만 수정 가능
    Features:
    - datetime-local 형식으로 초기값 설정
    - 성공/실패 메시지 표시
    """
    form_class = TransactionForm
    template_name = 'information/transaction_form.html'
    success_message = MSG_UPDATE_SUCCESS
    error_message = MSG_FORM_ERROR.format(action='수정')


# ============= DELETE VIEW =============
class TransactionDeleteView(TransactionBaseMixin, UserOwnerMixin, generic.DeleteView):
    """거래내역 삭제

    Permission: 본인 거래내역만 삭제 가능
    Features:
    - 삭제 확인 페이지
    - 성공 메시지 표시
    """
    template_name = 'information/transaction_confirm_delete.html'
    context_object_name = 'transaction'

    def delete(self, request, *args, **kwargs):
        """삭제 실행 및 성공 메시지"""
        messages.success(request, MSG_DELETE_SUCCESS)
        return super().delete(request, *args, **kwargs)


# ============= DASHBOARD VIEW =============
class DashboardView(LoginRequiredMixin, generic.TemplateView):
    """거래내역 대시보드

    Features:
    - 월별 수입/지출 집계
    - 카테고리별 지출 분석
    - 일별 거래 추이
    - CSS 막대그래프 시각화
    """
    template_name = 'information/dashboard.html'
    login_url = LOGIN_URL

    def get_context_data(self, **kwargs):
        """컨텍스트 데이터 구성"""
        context = super().get_context_data(**kwargs)

        try:
            # 기간 파라미터 검증
            period_str = self.request.GET.get('period', '6')
            months_back = validate_period_parameter(period_str)

            # 날짜 범위 계산
            start_date, end_date = get_month_range(months_back)

            # 컨텍스트 추가
            context.update({
                'selected_period': months_back,
                'period_options': [3, 6, 12, 24],
                **self._get_summary_stats(start_date, end_date),
                **self._get_monthly_data(start_date, end_date),
                **self._get_category_data(start_date, end_date),
                **self._get_daily_trend(end_date),
            })
        except Exception:
            # 전체 컨텍스트 생성 실패 시 기본값
            context.update({
                'selected_period': 6,
                'period_options': [3, 6, 12, 24],
                'total_income': Decimal('0'),
                'total_expense': Decimal('0'),
                'net_balance': Decimal('0'),
                'transaction_count': 0,
                'avg_amount': Decimal('0'),
                'monthly_data': [],
                'max_monthly_amount': Decimal('0'),
                'category_data': [],
                'total_category_expense': Decimal('0'),
                'daily_trend': [],
                'max_daily_amount': Decimal('0'),
            })

        return context

    def _get_base_queryset(self, start_date=None, end_date=None):
        """기본 쿼리셋 반환 (예외처리 포함)"""
        try:
            qs = Transaction.objects.filter(user=self.request.user)

            if start_date:
                qs = qs.filter(transaction_date__gte=start_date)
            if end_date:
                qs = qs.filter(transaction_date__lte=end_date)

            return qs
        except Exception:
            return Transaction.objects.none()

    def _get_summary_stats(self, start_date, end_date):
        """전체 요약 통계"""
        try:
            qs = self._get_base_queryset(start_date, end_date)

            # 공통 유틸리티 함수 사용
            stats = calculate_transaction_stats(
                qs,
                Transaction.DEPOSIT,
                Transaction.WITHDRAWAL,
                Transaction.SEOULPAY
            )

            # 거래 건수 및 평균
            transaction_count = qs.count()
            avg_amount = qs.aggregate(avg=Avg('amount'))['avg'] or Decimal('0')

            return {
                'total_income': stats['income'],
                'total_expense': stats['expense'],
                'net_balance': stats['balance'],
                'transaction_count': transaction_count,
                'avg_amount': avg_amount,
            }
        except Exception:
            return {
                'total_income': Decimal('0'),
                'total_expense': Decimal('0'),
                'net_balance': Decimal('0'),
                'transaction_count': 0,
                'avg_amount': Decimal('0'),
            }

    def _get_monthly_data(self, start_date, end_date):
        """월별 수입/지출 데이터"""
        try:
            qs = self._get_base_queryset(start_date, end_date)

            # 월별 집계
            monthly_stats = qs.annotate(
                month=TruncMonth('transaction_date')
            ).values('month', 'transaction_type').annotate(
                total=Sum('amount'),
                count=Count('id')
            ).order_by('month')

            # 데이터 구조화
            monthly_data = self._structure_monthly_data(monthly_stats)

            # 최대값 계산
            max_amount = self._calculate_max_amount(monthly_data)

            # 리스트 변환 및 비율 계산
            monthly_list = self._convert_monthly_to_list(monthly_data, max_amount)

            return {
                'monthly_data': monthly_list,
                'max_monthly_amount': max_amount,
            }
        except Exception:
            return {
                'monthly_data': [],
                'max_monthly_amount': Decimal('0'),
            }

    def _structure_monthly_data(self, monthly_stats):
        """월별 통계 데이터 구조화"""
        monthly_data = defaultdict(lambda: {
            'income': Decimal('0'),
            'expense': Decimal('0'),
            'count': 0,
        })

        for stat in monthly_stats:
            try:
                month_key = stat['month'].strftime('%Y-%m')
                if stat['transaction_type'] == Transaction.DEPOSIT:
                    monthly_data[month_key]['income'] = stat['total'] or Decimal('0')
                else:
                    monthly_data[month_key]['expense'] += stat['total'] or Decimal('0')
                monthly_data[month_key]['count'] += stat['count'] or 0
            except (KeyError, AttributeError, ValueError):
                continue

        return monthly_data

    def _calculate_max_amount(self, monthly_data):
        """월별 데이터에서 최대 금액 계산"""
        max_amount = Decimal('0')
        for data in monthly_data.values():
            try:
                max_amount = max(max_amount, data['income'], data['expense'])
            except (ValueError, TypeError):
                continue
        return max_amount

    def _convert_monthly_to_list(self, monthly_data, max_amount):
        """월별 데이터를 리스트로 변환"""
        monthly_list = []
        for month_key in sorted(monthly_data.keys()):
            try:
                data = monthly_data[month_key]

                monthly_list.append({
                    'month': month_key,
                    'month_display': datetime.strptime(month_key, '%Y-%m').strftime('%Y년 %m월'),
                    'income': data['income'],
                    'expense': data['expense'],
                    'balance': data['income'] - data['expense'],
                    'count': data['count'],
                    'income_percent': calculate_percentage(data['income'], max_amount),
                    'expense_percent': calculate_percentage(data['expense'], max_amount),
                })
            except (ValueError, KeyError):
                continue

        return monthly_list

    def _get_category_data(self, start_date, end_date):
        """카테고리별 지출 데이터"""
        try:
            qs = self._get_base_queryset(start_date, end_date).filter(
                transaction_type__in=[Transaction.WITHDRAWAL, Transaction.SEOULPAY]
            ).exclude(
                category=Transaction.HEALTH_POINT
            )

            # 카테고리별 집계
            category_stats = qs.values('category').annotate(
                total=Sum('amount'),
                count=Count('id')
            ).order_by('-total')

            # 전체 지출
            total_expense = sum(
                stat['total'] for stat in category_stats if stat['total']
            ) or Decimal('1')

            # 카테고리 정보 매핑
            category_dict = dict(Transaction.CATEGORY_CHOICES)

            # 데이터 구조화
            category_list = self._structure_category_data(
                category_stats, category_dict, total_expense
            )

            return {
                'category_data': category_list,
                'total_category_expense': total_expense,
            }
        except Exception:
            return {
                'category_data': [],
                'total_category_expense': Decimal('0'),
            }

    def _structure_category_data(self, category_stats, category_dict, total_expense):
        """카테고리 데이터 구조화"""
        category_list = []
        for stat in category_stats:
            try:
                amount = stat['total'] or Decimal('0')
                category_list.append({
                    'category': stat['category'],
                    'category_display': category_dict.get(
                        stat['category'], stat['category']
                    ),
                    'amount': amount,
                    'count': stat['count'] or 0,
                    'percent': calculate_percentage(amount, total_expense),
                })
            except (KeyError, ValueError):
                continue

        return category_list

    def _get_daily_trend(self, end_date):
        """최근 30일 일별 거래 추이"""
        try:
            start_date = end_date - timedelta(days=30)
            qs = self._get_base_queryset(start_date, end_date)

            # 일별 집계
            daily_stats = qs.annotate(
                date=TruncDate('transaction_date')
            ).values('date', 'transaction_type').annotate(
                total=Sum('amount')
            ).order_by('date')

            # 데이터 구조화
            daily_data = self._structure_daily_data(daily_stats)

            # 최대값 계산
            max_daily = self._calculate_max_daily(daily_data)

            # 리스트 변환
            daily_list = self._convert_daily_to_list(daily_data, max_daily)

            return {
                'daily_trend': list(reversed(daily_list)),
                'max_daily_amount': max_daily,
            }
        except Exception:
            return {
                'daily_trend': [],
                'max_daily_amount': Decimal('0'),
            }

    def _structure_daily_data(self, daily_stats):
        """일별 통계 데이터 구조화"""
        daily_data = defaultdict(lambda: {
            'income': Decimal('0'),
            'expense': Decimal('0'),
        })

        for stat in daily_stats:
            try:
                date_key = stat['date'].strftime('%Y-%m-%d')
                if stat['transaction_type'] == Transaction.DEPOSIT:
                    daily_data[date_key]['income'] = stat['total'] or Decimal('0')
                else:
                    daily_data[date_key]['expense'] += stat['total'] or Decimal('0')
            except (KeyError, AttributeError, ValueError):
                continue

        return daily_data

    def _calculate_max_daily(self, daily_data):
        """일별 데이터에서 최대 금액 계산"""
        max_daily = Decimal('0')
        for data in daily_data.values():
            try:
                max_daily = max(max_daily, data['income'], data['expense'])
            except (ValueError, TypeError):
                continue
        return max_daily

    def _convert_daily_to_list(self, daily_data, max_daily):
        """일별 데이터를 리스트로 변환 (최근 14일)"""
        daily_list = []
        for date_key in sorted(daily_data.keys(), reverse=True)[:14]:
            try:
                data = daily_data[date_key]
                daily_list.append({
                    'date': date_key,
                    'date_display': datetime.strptime(date_key, '%Y-%m-%d').strftime('%m/%d'),
                    'income': data['income'],
                    'expense': data['expense'],
                    'balance': data['income'] - data['expense'],
                    'income_percent': calculate_percentage(data['income'], max_daily),
                    'expense_percent': calculate_percentage(data['expense'], max_daily),
                })
            except (ValueError, KeyError):
                continue

        return daily_list


# ============= INTEGRATED DASHBOARD VIEW =============
class IntegratedDashboardView(LoginRequiredMixin, TransactionFilterMixin, generic.ListView):
    """통합 대시보드 - 대시보드 + 거래내역 목록

    Features:
    - 상단: 대시보드 통계 및 그래프
    - 하단: 거래내역 목록 (검색/필터/페이징)
    """
    model = Transaction
    template_name = 'information/integrated_dashboard.html'
    context_object_name = 'transactions'
    login_url = LOGIN_URL
    paginate_by = 15  # 통합 페이지에서는 15개로 조정

    def get_queryset(self):
        """사용자 거래내역 + 검색/필터"""
        try:
            queryset = Transaction.objects.filter(user=self.request.user)
            queryset = self._apply_filters(queryset)
            return queryset
        except Exception:
            return Transaction.objects.none()

    def get_context_data(self, **kwargs):
        """컨텍스트 데이터 추가 (대시보드 + 필터 상태 + 포인트)"""
        context = super().get_context_data(**kwargs)

        try:
            # DashboardView의 컨텍스트 재사용
            dashboard_view = DashboardView()
            dashboard_view.request = self.request
            dashboard_context = dashboard_view.get_context_data()

            context.update(dashboard_context)

            # 필터 상태 추가
            context.update(self._get_filter_context())
        except Exception:
            # 대시보드 컨텍스트 생성 실패 시 기본값
            context.update(self._get_filter_context())

        # 포인트 데이터 추가
        try:
            profile, created = UserProfile.objects.get_or_create(user=self.request.user)
            point_transactions = Transaction.objects.filter(
                user=self.request.user,
                description__icontains='포인트'
            )[:10]
            context.update({
                'profile': profile,
                'points': profile.points,
                'point_transactions': point_transactions,
            })
        except Exception:
            context.update({
                'points': 0,
                'point_transactions': [],
            })

        return context



##

@login_required
def points_view(request):
    """포인트 관리 페이지

    Features:
    - 현재 포인트 잔액 표시
    - 포인트 거래 내역 표시
    - 서울페이 연동 버튼
    """
    # UserProfile 가져오기 또는 생성
    profile, created = UserProfile.objects.get_or_create(user=request.user)

    # 포인트 관련 거래내역 가져오기
    point_transactions = Transaction.objects.filter(
        user=request.user,
        description__icontains='포인트'
    )[:10]

    context = {
        'profile': profile,
        'points': profile.points,
        'point_transactions': point_transactions,
    }

    return render(request, 'information/points.html', context)


@login_required
@require_POST
def transfer_to_seoulpay(request):
    """서울페이로 포인트 전송

    Features:
    - 입력한 금액만큼 포인트 차감
    - Transaction 기록 생성
    - 서울페이 연동 (시뮬레이션)
    """
    # 전송할 포인트 금액 가져오기
    amount = request.POST.get('amount')

    try:
        amount = int(amount)
        if amount <= 0:
            messages.error(request, '전송할 포인트는 0보다 커야 합니다.')
            return redirect('information:integrated_dashboard')
    except (ValueError, TypeError):
        messages.error(request, '올바른 금액을 입력해주세요.')
        return redirect('information:integrated_dashboard')

    # UserProfile 가져오기
    try:
        profile = request.user.profile
    except UserProfile.DoesNotExist:
        profile = UserProfile.objects.create(user=request.user)

    # 포인트가 충분한지 확인
    if profile.points < amount:
        messages.error(request, f'포인트가 부족합니다. (현재: {profile.points:,}P, 필요: {amount:,}P)')
        return redirect('information:integrated_dashboard')

    # 포인트 차감
    profile.deduct_points(amount, '서울페이로 전송')

    # Transaction 기록 생성
    Transaction.objects.create(
        user=request.user,
        transaction_type=Transaction.SEOULPAY,
        amount=amount,
        category=Transaction.HEALTH_POINT,
        description='서울페이로 포인트 전송',
        balance_after=profile.points,
        transaction_date=timezone.now(),
        memo=f'{amount:,}P를 서울페이로 전송'
    )

    messages.success(request, f'{amount:,}P가 서울페이로 전송되었습니다! 💳')
    return redirect('information:integrated_dashboard')