from django.db import models
from django.contrib.auth.models import User
from django.core.validators import FileExtensionValidator, MaxLengthValidator
from django.core.exceptions import ValidationError


class ChallengeSet(models.Model):
    """챌린지 세트 - 음식이미지, 영수증, 레시피, 기록장을 하나로 묶음"""
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='challenge_sets')
    title = models.CharField(max_length=100, verbose_name='챌린지 제목', default='나의 챌린지')
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        ordering = ['-created_at']
        verbose_name = '챌린지 세트'
        verbose_name_plural = '챌린지 세트 목록'
    
    def __str__(self):
        return f"{self.user.username} - {self.title} ({self.created_at.date()})"



class FoodImage(models.Model):
   # ⭐ 새로 추가된 필드!
    challenge_set = models.OneToOneField(
        ChallengeSet, 
        on_delete=models.CASCADE, 
        related_name='food_image',
        null=True,
        blank=True
    )
    """테이블1: 음식 이미지 (5MB, 1000x1000px)"""
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='food_images')
    image = models.ImageField(
        upload_to='food_images/%Y/%m/%d/',
        validators=[FileExtensionValidator(['jpg', 'jpeg', 'png'])],
        help_text='최대 5MB, 1000x1000 픽셀 권장'
    )
    title = models.CharField(max_length=100, blank=True, verbose_name='제목')
    created_at = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        ordering = ['-created_at']
        verbose_name = '음식 이미지'
        verbose_name_plural = '음식 이미지 목록'
    
    def clean(self):
        if self.image:
            if self.image.size > 5 * 1024 * 1024:
                raise ValidationError('이미지 크기는 5MB를 초과할 수 없습니다.')
    
    def __str__(self):
        return f"{self.user.username} - {self.title or 'Untitled'}"


class Receipt(models.Model):
    # ⭐ 새로 추가된 필드!
    challenge_set = models.OneToOneField(
        ChallengeSet, 
        on_delete=models.CASCADE, 
        related_name='receipt',
        null=True,
        blank=True
    )
    """테이블2: 영수증 OCR"""
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='receipts')
    image = models.ImageField(upload_to='receipts/%Y/%m/%d/', verbose_name='영수증 이미지')
    ocr_text = models.TextField(blank=True, verbose_name='추출된 텍스트')
    is_processed = models.BooleanField(default=False, verbose_name='처리 완료')
    created_at = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        ordering = ['-created_at']
        verbose_name = '영수증'
        verbose_name_plural = '영수증 목록'
    
    def __str__(self):
        return f"{self.user.username} - Receipt {self.id}"



class Recipe(models.Model):
    # ⭐ 새로 추가된 필드!
    challenge_set = models.OneToOneField(
        ChallengeSet, 
        on_delete=models.CASCADE, 
        related_name='recipe',
        null=True,
        blank=True
    )

    """테이블3: 나의 레시피 (공개형, 300자 제한)"""
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='recipes')
    title = models.CharField(max_length=100, verbose_name='레시피 제목')
    content = models.TextField(
        max_length=300,
        validators=[MaxLengthValidator(300)],
        verbose_name='레시피 내용'
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    views = models.IntegerField(default=0, verbose_name='조회수')
    
    likes = models.ManyToManyField(User, related_name='liked_recipes', blank=True)

    class Meta:
        ordering = ['-created_at']
        verbose_name = '레시피'
        verbose_name_plural = '레시피 목록'

    def __str__(self):
        return self.title
    
    def content_preview(self):
        """미리보기용 (50자)"""
        return self.content[:50] + '...' if len(self.content) > 50 else self.content

    # ⭐ 2. 좋아요 개수 메서드 추가 (새로 추가!)
    def total_likes(self):
        """총 좋아요 수"""
        return self.likes.count()



class Journal(models.Model):
    """테이블4: 기록장 (공개/비공개, 200자 제한)"""
    PUBLIC = 'public'
    PRIVATE = 'private'
    VISIBILITY_CHOICES = [
        (PUBLIC, '공개'),
        (PRIVATE, '비공개'),
    ]
    # ⭐ 새로 추가된 필드!
    challenge_set = models.OneToOneField(
        ChallengeSet, 
        on_delete=models.CASCADE, 
        related_name='journal',
        null=True,
        blank=True
    )

    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='journals')
    title = models.CharField(max_length=100, verbose_name='제목')
    content = models.TextField(
        max_length=200,
        validators=[MaxLengthValidator(200)],
        verbose_name='내용'
    )
    visibility = models.CharField(
        max_length=10,
        choices=VISIBILITY_CHOICES,
        default=PRIVATE,
        verbose_name='공개 설정'
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
class Meta:
        ordering = ['-created_at']
        verbose_name = '기록장'
        verbose_name_plural = '기록장 목록'
    
def __str__(self):
        return f"{self.title} ({self.get_visibility_display()})"
    
def content_preview(self):
        """미리보기용 (30자)"""
        return self.content[:30] + '...' if len(self.content) > 30 else self.content
