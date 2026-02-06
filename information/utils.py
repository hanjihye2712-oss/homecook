"""거래내역 관련 유틸리티 함수 모듈
중복 코드 제거 및 재사용성 향상
"""
from decimal import Decimal
from django.db.models import Sum
from django.utils import timezone
from datetime import timedelta


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


def get_current_month_range():
    """이번 달 시작일과 종료일 반환
    
    Returns:
        tuple: (month_start, month_end)
    """
    now = timezone.now()
    month_start = now.replace(day=1, hour=0, minute=0, second=0, microsecond=0)
    return month_start, now


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
    
    # 지출 합계
    expense = queryset.filter(
        transaction_type__in=[transaction_type_withdrawal, transaction_type_transfer]
    ).aggregate(total=Sum('amount'))['total'] or Decimal('0')
    
    return {
        'income': income,
        'expense': expense,
        'balance': income - expense,
    }


def safe_decimal_operation(operation, *args, default=Decimal('0')):
    """안전한 Decimal 연산
    
    Args:
        operation: 실행할 연산 함수
        *args: 연산에 필요한 인자들
        default: 오류 시 반환할 기본값
        
    Returns:
        Decimal: 연산 결과 또는 기본값
    """
    try:
        result = operation(*args)
        return result if result is not None else default
    except (ValueError, TypeError, ArithmeticError):
        return default


def format_amount(amount):
    """금액 포맷팅
    
    Args:
        amount: 포맷팅할 금액
        
    Returns:
        str: 쉼표가 포함된 금액 문자열 (예: "1,000원")
    """
    try:
        return f"{amount:,.0f}원" if amount else "0원"
    except (ValueError, TypeError):
        return "0원"


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
