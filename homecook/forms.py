from django import forms
from .models import FoodImage, Receipt, Recipe, Journal
from django.core.exceptions import ValidationError
from PIL import Image as PILImage


class FoodImageForm(forms.ModelForm):
    """음식 이미지 업로드 폼"""
    
    class Meta:
        model = FoodImage
        fields = ['image', 'title']
        widgets = {
            'title': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': '이미지 제목을 입력하세요 (선택사항)'
            }),
            'image': forms.FileInput(attrs={
                'class': 'form-control',
                'accept': 'image/jpeg,image/jpg,image/png'
            })
        }
        labels = {
            'title': '제목',
            'image': '이미지 파일'
        }
    
    def clean_image(self):
        image = self.cleaned_data.get('image')
        
        if image:
            # 용량 체크 (5MB)
            if image.size > 5 * 1024 * 1024:
                raise ValidationError('이미지 크기는 5MB를 초과할 수 없습니다.')
            
            # 이미지 형식 체크
            try:
                img = PILImage.open(image)
                img.verify()
                
                # 해상도 경고 (1000x1000 권장)
                if img.width < 500 or img.height < 500:
                    raise ValidationError('이미지 해상도는 최소 500x500 픽셀 이상이어야 합니다.')
                
            except Exception:
                raise ValidationError('올바른 이미지 파일이 아닙니다.')
        
        return image


class ReceiptForm(forms.ModelForm):
    """영수증 업로드 폼"""
    
    class Meta:
        model = Receipt
        fields = ['image']
        widgets = {
            'image': forms.FileInput(attrs={
                'class': 'form-control',
                'accept': 'image/*'
            })
        }
        labels = {
            'image': '영수증 이미지'
        }


class RecipeForm(forms.ModelForm):
    """레시피 작성 폼 (300자 제한)"""
    
    class Meta:
        model = Recipe
        fields = ['title', 'content']
        widgets = {
            'title': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': '레시피 제목을 입력하세요',
                'maxlength': '100'
            }),
            'content': forms.Textarea(attrs={
                'class': 'form-control',
                'placeholder': '레시피 내용을 입력하세요 (최대 300자)',
                'rows': 8,
                'maxlength': '300',
                'id': 'recipe-content'
            })
        }
        labels = {
            'title': '레시피 제목',
            'content': '레시피 내용'
        }
    
    def clean_content(self):
        content = self.cleaned_data.get('content')
        if len(content) > 300:
            raise ValidationError('레시피 내용은 300자를 초과할 수 없습니다.')
        return content


class JournalForm(forms.ModelForm):
    """기록장 작성 폼 (200자 제한, 공개/비공개)"""
    
    class Meta:
        model = Journal
        fields = ['title', 'content', 'visibility']
        widgets = {
            'title': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': '제목을 입력하세요',
                'maxlength': '100'
            }),
            'content': forms.Textarea(attrs={
                'class': 'form-control',
                'placeholder': '내용을 입력하세요 (최대 200자)',
                'rows': 6,
                'maxlength': '200',
                'id': 'journal-content'
            }),
            'visibility': forms.Select(attrs={
                'class': 'form-select'
            })
        }
        labels = {
            'title': '제목',
            'content': '내용',
            'visibility': '공개 설정'
        }
    
    def clean_content(self):
        content = self.cleaned_data.get('content')
        if len(content) > 200:
            raise ValidationError('기록장 내용은 200자를 초과할 수 없습니다.')
        return content