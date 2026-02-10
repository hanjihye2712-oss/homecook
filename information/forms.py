from django import forms
from .models import Transaction
from django.core.exceptions import ValidationError


class TransactionForm(forms.ModelForm):
    """거래내역 생성/수정 폼"""
    description = forms.CharField(required=False, widget=forms.TextInput(attrs={
        'class': 'form-control',
        'placeholder': '거래 내용을 입력하세요',
        'maxlength': '200',
    }), label='거래 내용', max_length=200)

    class Meta:
        model = Transaction
        fields = ['transaction_type', 'amount', 'category', 'description',
                  'transaction_date']
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
            'transaction_date': forms.DateTimeInput(attrs={
                'class': 'form-control',
                'type': 'datetime-local',
                'required': True
            }),
        }
        labels = {
            'transaction_type': '거래 유형',
            'amount': '금액',
            'category': '카테고리',
            'transaction_date': '거래 일시',
        }

    def clean_amount(self):
        """금액 검증"""
        amount = self.cleaned_data.get('amount')
        if amount and amount <= 0:
            raise ValidationError('금액은 0보다 커야 합니다.')
        return amount
