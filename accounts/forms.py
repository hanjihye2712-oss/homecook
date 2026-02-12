from django.contrib.auth.forms import UserCreationForm
from django.contrib.auth.models import User
from django import forms


class CustomUserCreationForm(UserCreationForm):
    class Meta(UserCreationForm.Meta):
        model = User
        fields = UserCreationForm.Meta.fields

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['username'].max_length = 15
        self.fields['username'].help_text = '15자 이하 문자, 숫자 그리고 @/./+/-/_만 가능합니다.'
        self.fields['username'].widget.attrs['maxlength'] = 15
