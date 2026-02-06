from django.db import models
from django.contrib.auth.models import User
from django.core.validators import MinValueValidator
from django.core.exceptions import ValidationError


class Transaction(models.Model):
    """계좌 거래내역 모델"""
    
    # 거래 유형
    DEPOSIT = 'deposit'
    WITHDRAWAL = 'withdrawal'
    TRANSFER = 'transfer'
    
    TRANSACTION_TYPE_CHOICES = [
        (DEPOSIT, '입금'),
        (WITHDRAWAL, '출금'),
        (TRANSFER, '이체'),
    ]
    
    # 카테고리
    FOOD = 'food'
    TRANSPORT = 'transport'
    SHOPPING = 'shopping'
    UTILITY = 'utility'
    ENTERTAINMENT = 'entertainment'
    INCOME = 'income'
    OTHER = 'other'
    
    CATEGORY_CHOICES = [
        (FOOD, '식비'),
        (TRANSPORT, '교통비'),
        (SHOPPING, '쇼핑'),
        (UTILITY, '공과금'),
        (ENTERTAINMENT, '여가/문화'),
        (INCOME, '수입'),
        (OTHER, '기타'),
    ]
    
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='transactions', verbose_name='사용자')
    transaction_type = models.CharField(max_length=20, choices=TRANSACTION_TYPE_CHOICES, verbose_name='거래 유형')
    amount = models.DecimalField(max_digits=12, decimal_places=0, validators=[MinValueValidator(0)], verbose_name='금액')
    category = models.CharField(max_length=20, choices=CATEGORY_CHOICES, verbose_name='카테고리')
    description = models.CharField(max_length=200, verbose_name='내용', help_text='거래 내용을 입력하세요 (최대 200자)')
    balance_after = models.DecimalField(max_digits=12, decimal_places=0, blank=True, null=True, verbose_name='거래 후 잔액')
    transaction_date = models.DateTimeField(verbose_name='거래 일시')
    created_at = models.DateTimeField(auto_now_add=True, verbose_name='등록 일시')
    updated_at = models.DateTimeField(auto_now=True, verbose_name='수정 일시')
    memo = models.TextField(blank=True, max_length=500, verbose_name='메모', help_text='추가 메모 (선택사항, 최대 500자)')
    
    class Meta:
        ordering = ['-transaction_date', '-created_at']
        verbose_name = '거래내역'
        verbose_name_plural = '거래내역 목록'
        indexes = [
            models.Index(fields=['user', '-transaction_date']),
            models.Index(fields=['transaction_type']),
            models.Index(fields=['category']),
        ]
    
    def __str__(self):
        return f"{self.get_transaction_type_display()} - {self.amount:,}원 ({self.description})"
    
    def clean(self):
        """금액 유효성 검사"""
        if self.amount <= 0:
            raise ValidationError('금액은 0보다 커야 합니다.')
    
    def get_amount_display(self):
        """금액을 포맷팅하여 반환"""
        return f"{self.amount:,.0f}원"
    
    def get_balance_display(self):
        """잔액을 포맷팅하여 반환"""
        return f"{self.balance_after:,.0f}원" if self.balance_after else "-"
    
    def is_income(self):
        """수입 거래인지 확인"""
        return self.transaction_type == self.DEPOSIT or self.category == self.INCOME
    
    def is_expense(self):
        """지출 거래인지 확인"""
        return self.transaction_type in [self.WITHDRAWAL, self.TRANSFER]
