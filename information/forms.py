from django import forms
from .models import Transaction
from django.core.exceptions import ValidationError


class TransactionForm(forms.ModelForm):
    """거래내역 생성/수정 폼"""
    
    class Meta:
        model = Transaction
        fields = ['transaction_type', 'amount', 'category', 'description', 
                  'balance_after', 'transaction_date', 'memo']
        widgets = {
            'transaction_type': forms.Select(attrs={'class': 'form-select', 'required': True}),
            'amount': forms.NumberInput(attrs={
                'class': 'form-control',
                'placeholder': '금액을 입력하세요',
                'min': '0',
                'step': '1',
                'required': True
            }),
            'category': forms.Select(attrs={'class': 'form-select', 'required': True}),
            'description': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': '거래 내용을 입력하세요',
                'maxlength': '200',
                'required': True
            }),
            'balance_after': forms.NumberInput(attrs={
                'class': 'form-control',
                'placeholder': '거래 후 잔액 (선택사항)',
                'min': '0',
                'step': '1'
            }),
            'transaction_date': forms.DateTimeInput(attrs={
                'class': 'form-control',
                'type': 'datetime-local',
                'required': True
            }),
            'memo': forms.Textarea(attrs={
                'class': 'form-control',
                'placeholder': '추가 메모를 입력하세요 (선택사항)',
                'rows': 3,
                'maxlength': '500'
            })
        }
        labels = {
            'transaction_type': '거래 유형',
            'amount': '금액',
            'category': '카테고리',
            'description': '거래 내용',
            'balance_after': '거래 후 잔액',
            'transaction_date': '거래 일시',
            'memo': '메모'
        }
    
    def clean_amount(self):
        """금액 검증"""
        amount = self.cleaned_data.get('amount')
        if amount and amount <= 0:
            raise ValidationError('금액은 0보다 커야 합니다.')
        return amount
    
    def clean_balance_after(self):
        """잔액 검증"""
        balance = self.cleaned_data.get('balance_after')
        if balance is not None and balance < 0:
            raise ValidationError('잔액은 음수일 수 없습니다.')
        return balance
