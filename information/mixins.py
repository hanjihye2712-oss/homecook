"""거래내역 필터링 공통 믹스인
"""
from django.db.models import Q
from .models import Transaction


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
            'categories': Transaction.CATEGORY_CHOICES,
            'transaction_types': Transaction.TRANSACTION_TYPE_CHOICES,
        }
