from django import forms
from .models import FoodImage, Receipt, Recipe, Journal


class FoodImageForm(forms.ModelForm):
    """음식 이미지 업로드 폼"""
    class Meta:
        model = FoodImage
        fields = ['image', 'title']
        widgets = {
            'image': forms.FileInput(attrs={
                'class': 'form-control',
                'id': 'id_image'
            }),
            'title': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': '음식 이미지 제목 (선택사항)'
            }),
        }
        labels = {
            'image': '이미지',
            'title': '제목',
        }
    
    def clean_image(self):
        """이미지 파일 크기 검증 (5MB)"""
        image = self.cleaned_data.get('image')
        if image:
            if image.size > 5 * 1024 * 1024:  # 5MB
                raise forms.ValidationError('이미지 크기는 5MB를 초과할 수 없습니다.')
        return image


class ReceiptForm(forms.ModelForm):
    """영수증 이미지 업로드 폼"""
    class Meta:
        model = Receipt
        fields = ['image']
        widgets = {
            'image': forms.FileInput(attrs={
                'class': 'form-control',
                'id': 'id_receipt_image'
            }),
        }
        labels = {
            'image': '영수증 이미지',
        }


class RecipeForm(forms.ModelForm):
    """레시피 작성 폼 (300자 제한)"""
    class Meta:
        model = Recipe
        fields = ['title', 'content']
        widgets = {
            'title': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': '레시피 제목을 입력하세요'
            }),
            'content': forms.Textarea(attrs={
                'class': 'form-control',
                'id': 'recipe-content',
                'rows': 8,
                'placeholder': '레시피 내용을 입력하세요 (최대 300자)',
                'maxlength': 300
            }),
        }
        labels = {
            'title': '레시피 제목',
            'content': '레시피 내용',
        }
    
    def clean_content(self):
        """내용 글자 수 검증 (300자)"""
        content = self.cleaned_data.get('content')
        if content and len(content) > 300:
            raise forms.ValidationError('레시피 내용은 300자를 초과할 수 없습니다.')
        return content


class JournalForm(forms.ModelForm):
    """기록장 작성 폼 (200자 제한, 공개/비공개)"""
    class Meta:
        model = Journal
        fields = ['title', 'content', 'visibility']
        widgets = {
            'title': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': '기록 제목을 입력하세요'
            }),
            'content': forms.Textarea(attrs={
                'class': 'form-control',
                'id': 'journal-content',
                'rows': 6,
                'placeholder': '기록 내용을 입력하세요 (최대 200자)',
                'maxlength': 200
            }),
            'visibility': forms.Select(attrs={
                'class': 'form-select'
            }),
        }
        labels = {
            'title': '기록 제목',
            'content': '기록 내용',
            'visibility': '공개 설정',
        }
    
    def clean_content(self):
        """내용 글자 수 검증 (200자)"""
        content = self.cleaned_data.get('content')
        if content and len(content) > 200:
            raise forms.ValidationError('기록 내용은 200자를 초과할 수 없습니다.')
        return content


class ChallengeSetCreateForm(forms.Form):
    """
    통합 챌린지 세트 생성 폼
    한 페이지에서 음식이미지, 영수증, 레시피, 기록장을 모두 입력 가능
    """
    
    # ========================================
    # 1. 챌린지 세트 제목 (필수)
    # ========================================
    set_title = forms.CharField(
        max_length=100,
        required=True,
        widget=forms.TextInput(attrs={
            'class': 'form-control form-control-lg',
            'placeholder': '예: 2024년 1월 1주차 요리 챌린지'
        }),
        label='챌린지 제목',
        help_text='이 챌린지 세트를 대표하는 제목을 입력하세요'
    )
    
    # ========================================
    # 2. 음식 이미지 (선택)
    # ========================================
    food_image = forms.ImageField(
        required=False,
        widget=forms.FileInput(attrs={
            'class': 'form-control',
            'id': 'id_food_image',
            'accept': 'image/*'
        }),
        label='음식 이미지',
        help_text='최대 5MB, 권장 해상도 1000x1000px'
    )
    
    food_image_title = forms.CharField(
        max_length=100,
        required=False,
        widget=forms.TextInput(attrs={
            'class': 'form-control',
            'placeholder': '음식 이미지 제목 (선택사항)'
        }),
        label='이미지 제목'
    )
    
    # ========================================
    # 3. 영수증 (선택)
    # ========================================
    receipt_image = forms.ImageField(
        required=False,
        widget=forms.FileInput(attrs={
            'class': 'form-control',
            'id': 'id_receipt_image',
            'accept': 'image/*'
        }),
        label='영수증 이미지',
        help_text='업로드 시 자동으로 텍스트를 추출합니다 (OCR)'
    )
    
    # ========================================
    # 4. 레시피 (선택)
    # ========================================
    recipe_title = forms.CharField(
        max_length=100,
        required=False,
        widget=forms.TextInput(attrs={
            'class': 'form-control',
            'placeholder': '레시피 제목을 입력하세요'
        }),
        label='레시피 제목'
    )
    
    recipe_content = forms.CharField(
        max_length=300,
        required=False,
        widget=forms.Textarea(attrs={
            'class': 'form-control',
            'id': 'recipe-content',
            'rows': 6,
            'placeholder': '레시피 내용을 입력하세요 (최대 300자)',
            'maxlength': 300
        }),
        label='레시피 내용',
        help_text='요리 과정이나 재료를 자세히 적어주세요'
    )
    
    # ========================================
    # 5. 기록장 (선택)
    # ========================================
    journal_title = forms.CharField(
        max_length=100,
        required=False,
        widget=forms.TextInput(attrs={
            'class': 'form-control',
            'placeholder': '기록 제목을 입력하세요'
        }),
        label='기록 제목'
    )
    
    journal_content = forms.CharField(
        max_length=200,
        required=False,
        widget=forms.Textarea(attrs={
            'class': 'form-control',
            'id': 'journal-content',
            'rows': 5,
            'placeholder': '오늘의 요리 경험을 기록하세요 (최대 200자)',
            'maxlength': 200
        }),
        label='기록 내용',
        help_text='오늘의 요리 경험, 느낀 점 등을 자유롭게 작성하세요'
    )
    
    journal_visibility = forms.ChoiceField(
        choices=[
            ('private', '비공개'),
            ('public', '공개'),
        ],
        required=False,
        initial='private',
        widget=forms.Select(attrs={
            'class': 'form-select'
        }),
        label='공개 설정',
        help_text='공개로 설정하면 다른 사용자도 볼 수 있습니다'
    )
    
    # ========================================
    # 유효성 검증
    # ========================================
    
    def clean_food_image(self):
        """음식 이미지 파일 크기 검증"""
        image = self.cleaned_data.get('food_image')
        if image:
            if image.size > 5 * 1024 * 1024:  # 5MB
                raise forms.ValidationError('이미지 크기는 5MB를 초과할 수 없습니다.')
        return image
    
    def clean_receipt_image(self):
        """영수증 이미지 파일 크기 검증"""
        image = self.cleaned_data.get('receipt_image')
        if image:
            if image.size > 10 * 1024 * 1024:  # 10MB
                raise forms.ValidationError('영수증 이미지 크기는 10MB를 초과할 수 없습니다.')
        return image
    
    def clean_recipe_content(self):
        """레시피 내용 글자 수 검증"""
        content = self.cleaned_data.get('recipe_content')
        if content and len(content) > 300:
            raise forms.ValidationError('레시피 내용은 300자를 초과할 수 없습니다.')
        return content
    
    def clean_journal_content(self):
        """기록장 내용 글자 수 검증"""
        content = self.cleaned_data.get('journal_content')
        if content and len(content) > 200:
            raise forms.ValidationError('기록 내용은 200자를 초과할 수 없습니다.')
        return content
    
    def clean(self):
        """전체 폼 유효성 검증"""
        cleaned_data = super().clean()
        
        # 레시피: 제목과 내용 둘 다 있거나 둘 다 없어야 함
        recipe_title = cleaned_data.get('recipe_title')
        recipe_content = cleaned_data.get('recipe_content')
        
        if recipe_title and not recipe_content:
            raise forms.ValidationError('레시피 제목을 입력했다면 내용도 입력해주세요.')
        
        if recipe_content and not recipe_title:
            raise forms.ValidationError('레시피 내용을 입력했다면 제목도 입력해주세요.')
        
        # 기록장: 제목과 내용 둘 다 있거나 둘 다 없어야 함
        journal_title = cleaned_data.get('journal_title')
        journal_content = cleaned_data.get('journal_content')
        
        if journal_title and not journal_content:
            raise forms.ValidationError('기록 제목을 입력했다면 내용도 입력해주세요.')
        
        if journal_content and not journal_title:
            raise forms.ValidationError('기록 내용을 입력했다면 제목도 입력해주세요.')
        
        return cleaned_data