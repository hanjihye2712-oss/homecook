from django.contrib import admin
from .models import Transaction, Account


@admin.register(Account)
class AccountAdmin(admin.ModelAdmin):
    """계좌 관리자 페이지"""
    list_display = ['id', 'user', 'bank_name', 'account_number', 'account_alias', 'balance', 'is_active', 'created_at']
    list_filter = ['bank_name', 'is_active', 'created_at', 'user']
    search_fields = ['account_number', 'account_alias', 'user__username']
    date_hierarchy = 'created_at'
    ordering = ['-created_at']

    fieldsets = (
        ('기본 정보', {
            'fields': ('user', 'bank_name', 'account_number', 'account_alias')
        }),
        ('계좌 상세', {
            'fields': ('balance', 'is_active')
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


@admin.register(Transaction)
class TransactionAdmin(admin.ModelAdmin):
    """거래내역 관리자 페이지"""
    list_display = ['id', 'user', 'account', 'transaction_type', 'amount', 'category', 'description', 'transaction_date']
    list_filter = ['transaction_type', 'category', 'transaction_date', 'user', 'account']
    search_fields = ['description', 'memo', 'user__username']
    date_hierarchy = 'transaction_date'
    ordering = ['-transaction_date']

    fieldsets = (
        ('기본 정보', {
            'fields': ('user', 'account', 'transaction_type', 'amount', 'category')
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
