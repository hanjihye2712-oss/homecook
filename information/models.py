from django.db import models
from django.contrib.auth.models import User
from django.core.validators import MinValueValidator
from django.core.exceptions import ValidationError


class Account(models.Model):
    """계좌 모델"""

    # 은행 상수
    KB = 'kb'
    SHINHAN = 'shinhan'
    WOORI = 'woori'
    HANA = 'hana'
    NH = 'nh'
    IBK = 'ibk'
    KAKAO = 'kakao'
    TOSS = 'toss'
    OTHER_BANK = 'other'

    BANK_CHOICES = [
        (KB, 'KB국민'),
        (SHINHAN, '신한'),
        (WOORI, '우리'),
        (HANA, '하나'),
        (NH, 'NH농협'),
        (IBK, 'IBK기업'),
        (KAKAO, '카카오뱅크'),
        (TOSS, '토스뱅크'),
        (OTHER_BANK, '기타'),
    ]

    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='accounts_info', verbose_name='사용자')
    bank_name = models.CharField(max_length=20, choices=BANK_CHOICES, verbose_name='은행명')
    account_number = models.CharField(max_length=30, verbose_name='계좌번호', help_text='계좌번호를 입력하세요 (최대 30자)')
    account_alias = models.CharField(max_length=50, blank=True, default='', verbose_name='계좌 별칭', help_text='구분하기 쉬운 별칭을 입력하세요 (선택사항)')
    balance = models.DecimalField(max_digits=14, decimal_places=0, default=0, validators=[MinValueValidator(0)], verbose_name='잔액')
    is_active = models.BooleanField(default=True, verbose_name='활성 상태')
    created_at = models.DateTimeField(auto_now_add=True, verbose_name='등록 일시')
    updated_at = models.DateTimeField(auto_now=True, verbose_name='수정 일시')

    class Meta:
        ordering = ['-created_at']
        verbose_name = '계좌'
        verbose_name_plural = '계좌 목록'
        indexes = [
            models.Index(fields=['user', '-created_at']),
            models.Index(fields=['bank_name']),
        ]

    def __str__(self):
        alias = f" ({self.account_alias})" if self.account_alias else ""
        return f"{self.get_bank_name_display()} {self.get_masked_account_number()}{alias}"

    def clean(self):
        """잔액 유효성 검사"""
        if self.balance < 0:
            raise ValidationError('잔액은 0 이상이어야 합니다.')

    def get_balance_display(self):
        """잔액을 포맷팅하여 반환"""
        return f"{self.balance:,.0f}원"

    def get_masked_account_number(self):
        """계좌번호 마스킹 (앞 2자리 + * + 뒤 2자리)"""
        num = self.account_number.replace('-', '')
        if len(num) > 4:
            return num[:2] + '*' * (len(num) - 4) + num[-2:]
        return num


class Transaction(models.Model):
    """계좌 거래내역 모델"""
    
    # 거래 유형
    DEPOSIT = 'deposit'
    WITHDRAWAL = 'withdrawal'
    SEOULPAY = 'seoulpay'

    TRANSACTION_TYPE_CHOICES = [
        (DEPOSIT, '입금'),
        (WITHDRAWAL, '출금'),
        (SEOULPAY, '서울페이'),
    ]

    # 카테고리
    SALARY = 'salary'
    ALLOWANCE = 'allowance'
    FOOD = 'food'
    TRANSPORT = 'transport'
    SHOPPING = 'shopping'
    UTILITY = 'utility'
    ENTERTAINMENT = 'entertainment'
    HEALTH_POINT = 'health_point'
    RENT = 'rent'
    INTEREST = 'interest'
    MAINTENANCE = 'maintenance'
    OTHER = 'other'

    CATEGORY_CHOICES = [
        (SALARY, '월급'),
        (ALLOWANCE, '용돈'),
        (FOOD, '식비'),
        (TRANSPORT, '교통비'),
        (SHOPPING, '쇼핑'),
        (UTILITY, '공과금'),
        (ENTERTAINMENT, '여가/문화'),
        (HEALTH_POINT, '건강 포인트'),
        (RENT, '월세'),
        (INTEREST, '이자'),
        (MAINTENANCE, '관리비'),
        (OTHER, '기타'),
    ]
    
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='transactions', verbose_name='사용자')
    account = models.ForeignKey('Account', on_delete=models.SET_NULL, null=True, blank=True, related_name='transactions', verbose_name='계좌')
    transaction_type = models.CharField(max_length=20, choices=TRANSACTION_TYPE_CHOICES, verbose_name='거래 유형')
    amount = models.DecimalField(max_digits=12, decimal_places=0, validators=[MinValueValidator(0)], verbose_name='금액')
    category = models.CharField(max_length=20, choices=CATEGORY_CHOICES, verbose_name='카테고리')
    description = models.CharField(max_length=200, blank=True, default='', verbose_name='내용', help_text='거래 내용을 입력하세요 (선택사항, 최대 200자)')
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
        return self.transaction_type == self.DEPOSIT

    def is_expense(self):
        """지출 거래인지 확인"""
        return self.transaction_type in [self.WITHDRAWAL, self.SEOULPAY] and self.category != self.HEALTH_POINT
