from django.views import generic
from django.contrib.auth.mixins import LoginRequiredMixin, UserPassesTestMixin
from django.urls import reverse_lazy
from django.contrib import messages
from django.db.models import Sum, Q
from django.utils import timezone
from django.core.exceptions import ObjectDoesNotExist
from .models import Transaction
from .forms import TransactionForm


# ============= CONSTANTS =============
LOGIN_URL = '/accounts/login/'
SUCCESS_URL = reverse_lazy('information:transaction_list')

# 메시지 템플릿
MSG_CREATE_SUCCESS = '{type} 거래내역이 등록되었습니다! (금액: {amount}원) 💰'
MSG_UPDATE_SUCCESS = '거래내역이 성공적으로 수정되었습니다! ✏️'
MSG_DELETE_SUCCESS = '거래내역이 성공적으로 삭제되었습니다! 🗑️'
MSG_FORM_ERROR = '거래내역 {action}에 실패했습니다. 입력 내용을 확인해주세요.'


# ============= BASE MIXINS =============
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
class TransactionListView(TransactionBaseMixin, generic.ListView):
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
        queryset = Transaction.objects.filter(user=self.request.user)
        queryset = self._apply_filters(queryset)
        return queryset
    
    def _apply_filters(self, queryset):
        """검색 및 필터 적용"""
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
        
        return queryset
    
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
            month_start = timezone.now().replace(
                day=1, hour=0, minute=0, second=0, microsecond=0
            )
            
            month_trans = Transaction.objects.filter(
                user=self.request.user,
                transaction_date__gte=month_start
            )
            
            # 수입 합계
            income = month_trans.filter(
                transaction_type='deposit'
            ).aggregate(total=Sum('amount'))['total'] or 0
            
            # 지출 합계
            expense = month_trans.filter(
                transaction_type__in=['withdrawal', 'transfer']
            ).aggregate(total=Sum('amount'))['total'] or 0
            
            return {
                'monthly_income': income,
                'monthly_expense': expense,
                'monthly_balance': income - expense,
            }
        except Exception:
            # 통계 계산 실패 시 기본값
            return {
                'monthly_income': 0,
                'monthly_expense': 0,
                'monthly_balance': 0,
            }
    
    def _get_filter_context(self):
        """필터 상태 유지를 위한 컨텍스트"""
        return {
            'selected_category': self.request.GET.get('category', ''),
            'selected_type': self.request.GET.get('type', ''),
            'search_query': self.request.GET.get('search', ''),
            'categories': Transaction.CATEGORY_CHOICES,
            'transaction_types': Transaction.TRANSACTION_TYPE_CHOICES,
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