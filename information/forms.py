from django import forms
from .models import Transaction, Account
from django.core.exceptions import ValidationError


class AccountForm(forms.ModelForm):
    """계좌 생성/수정 폼"""

    class Meta:
        model = Account
        fields = ['bank_name', 'account_number', 'account_alias', 'balance', 'is_active']
        widgets = {
            'bank_name': forms.Select(attrs={'class': 'form-select', 'required': True}),
            'account_number': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': '계좌번호를 입력하세요',
                'maxlength': '30',
                'required': True,
            }),
            'account_alias': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': '계좌 별칭 (선택사항)',
                'maxlength': '50',
            }),
            'balance': forms.NumberInput(attrs={
                'class': 'form-control',
                'placeholder': '현재 잔액',
                'min': '0',
                'step': '1',
                'required': True,
            }),
            'is_active': forms.CheckboxInput(attrs={
                'class': 'form-check-input',
            }),
        }
        labels = {
            'bank_name': '은행명',
            'account_number': '계좌번호',
            'account_alias': '계좌 별칭',
            'balance': '잔액',
            'is_active': '활성 상태',
        }

    def clean_account_number(self):
        """계좌번호 검증 - 숫자와 하이픈만 허용"""
        account_number = self.cleaned_data.get('account_number')
        if account_number:
            cleaned = account_number.replace('-', '')
            if not cleaned.isdigit():
                raise ValidationError('계좌번호는 숫자와 하이픈(-)만 입력 가능합니다.')
        return account_number


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
                  'transaction_date', 'account']
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
            'account': forms.Select(attrs={'class': 'form-select'}),
        }
        labels = {
            'transaction_type': '거래 유형',
            'amount': '금액',
            'category': '카테고리',
            'transaction_date': '거래 일시',
            'account': '계좌',
        }

    def __init__(self, *args, **kwargs):
        self.user = kwargs.pop('user', None)
        super().__init__(*args, **kwargs)
        if self.user:
            self.fields['account'].queryset = Account.objects.filter(
                user=self.user, is_active=True
            )
        else:
            self.fields['account'].queryset = Account.objects.none()
        self.fields['account'].required = False
        self.fields['account'].empty_label = '계좌 선택 (선택사항)'

    def clean_amount(self):
        """금액 검증"""
        amount = self.cleaned_data.get('amount')
        if amount and amount <= 0:
            raise ValidationError('금액은 0보다 커야 합니다.')
        return amount
