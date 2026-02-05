from django.contrib import admin
from .models import Transaction


@admin.register(Transaction)
class TransactionAdmin(admin.ModelAdmin):
    """거래내역 관리자 페이지"""
    list_display = ['id', 'user', 'transaction_type', 'amount', 'category', 'description', 'transaction_date']
    list_filter = ['transaction_type', 'category', 'transaction_date', 'user']
    search_fields = ['description', 'memo', 'user__username']
    date_hierarchy = 'transaction_date'
    ordering = ['-transaction_date']
    
    fieldsets = (
        ('기본 정보', {
            'fields': ('user', 'transaction_type', 'amount', 'category')
        }),
        ('거래 상세', {
            'fields': ('description', 'balance_after', 'transaction_date')
        }),
        ('추가 정보', {
            'fields': ('memo',),
            'classes': ('collapse',)
        }),
        ('시스템 정보', {
            'fields': ('created_at', 'updated_at'),
            'classes': ('collapse',)
        }),
    )
    
    readonly_fields = ['created_at', 'updated_at']
    
    def get_readonly_fields(self, request, obj=None):
        """수정 시 사용자는 변경 불가"""
        if obj:
            return self.readonly_fields + ['user']
        return self.readonly_fields
