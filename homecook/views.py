from django.http import HttpResponse
from django.views import generic
from django.contrib.auth.mixins import LoginRequiredMixin
from django.db.models import Q
from django.urls import reverse_lazy
from django.contrib import messages
from .models import FoodImage, Receipt, Recipe, Journal
from .forms import FoodImageForm, ReceiptForm, RecipeForm, JournalForm
import pytesseract
from PIL import Image as PILImage


# ============= LANDING VIEW =============
class HomecookLandingView(generic.ListView):
    """홈쿡 랜딩 페이지 - 다른 사람들의 최근 음식 사진 8개 표시"""
    template_name = 'homecook/landing.html'
    context_object_name = 'recent_food_images'
    
    def get_queryset(self):
        """모든 사용자의 최근 음식 사진 8개"""
        return FoodImage.objects.all()[:8]


# ============= MY CHALLENGE VIEW =============
class HomecookMyChallengeView(LoginRequiredMixin, generic.ListView):
    """My Challenge 페이지 - 로그인한 사용자의 4개 테이블 데이터"""
    template_name = 'homecook/my_challenge.html'
    context_object_name = 'food_images'
    login_url = '/admin/login/'  # 로그인 페이지 URL
    
    def get_queryset(self):
        """로그인한 사용자의 음식 이미지 최신 4개"""
        return FoodImage.objects.filter(user=self.request.user)[:4]
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        
        # 로그인한 사용자의 데이터만 표시
        context['receipts'] = Receipt.objects.filter(user=self.request.user)[:4]
        context['recipes'] = Recipe.objects.filter(user=self.request.user)[:4]
        context['journals'] = Journal.objects.filter(user=self.request.user)[:4]
        
        # 다른 사람들의 공개 레시피 (참고용)
        context['public_recipes'] = Recipe.objects.exclude(user=self.request.user)[:4]
        
        return context


# ============= CREATE VIEWS =============

class HomecookFoodImageCreateView(LoginRequiredMixin, generic.CreateView):
    """음식 이미지 업로드 (5MB, 1000x1000px)"""
    model = FoodImage
    form_class = FoodImageForm
    template_name = 'homecook/food_image_form.html'
    success_url = reverse_lazy('homecook:my_challenge')
    login_url = '/admin/login/'
    
    def form_valid(self, form):
        form.instance.user = self.request.user
        
        # 이미지 해상도 확인
        image = form.cleaned_data['image']
        img = PILImage.open(image)
        
        if img.width != 1000 or img.height != 1000:
            messages.warning(
                self.request,
                f'권장 해상도는 1000x1000입니다. (현재: {img.width}x{img.height}px)'
            )
        
        messages.success(self.request, '음식 이미지가 성공적으로 업로드되었습니다! 🍽️')
        return super().form_valid(form)
    
    def form_invalid(self, form):
        messages.error(self.request, '이미지 업로드에 실패했습니다. 다시 시도해주세요.')
        return super().form_invalid(form)


class HomecookReceiptCreateView(LoginRequiredMixin, generic.CreateView):
    """영수증 업로드 및 OCR 처리"""
    model = Receipt
    form_class = ReceiptForm
    template_name = 'homecook/receipt_form.html'
    success_url = reverse_lazy('homecook:my_challenge')
    login_url = '/admin/login/'
    
    def form_valid(self, form):
        form.instance.user = self.request.user
        response = super().form_valid(form)
        
        # OCR 처리
        try:
            receipt = self.object
            img = PILImage.open(receipt.image.path)
            
            # Tesseract OCR 실행 (한글+영어)
            ocr_text = pytesseract.image_to_string(img, lang='kor+eng')
            
            receipt.ocr_text = ocr_text.strip()
            receipt.is_processed = True
            receipt.save()
            
            messages.success(self.request, '영수증이 업로드되고 텍스트가 추출되었습니다! 🧾')
        except Exception as e:
            messages.warning(
                self.request,
                f'영수증은 업로드되었으나 OCR 처리 중 오류가 발생했습니다: {str(e)}'
            )
        
        return response
    
    def form_invalid(self, form):
        messages.error(self.request, '영수증 업로드에 실패했습니다.')
        return super().form_invalid(form)


class HomecookRecipeCreateView(LoginRequiredMixin, generic.CreateView):
    """레시피 작성 (공개형, 300자 제한)"""
    model = Recipe
    form_class = RecipeForm
    template_name = 'homecook/recipe_form.html'
    success_url = reverse_lazy('homecook:my_challenge')
    login_url = '/admin/login/'
    
    def form_valid(self, form):
        form.instance.user = self.request.user
        messages.success(self.request, '레시피가 성공적으로 등록되었습니다! 👨‍🍳')
        return super().form_valid(form)
    
    def form_invalid(self, form):
        messages.error(self.request, '레시피 등록에 실패했습니다.')
        return super().form_invalid(form)


class HomecookJournalCreateView(LoginRequiredMixin, generic.CreateView):
    """기록장 작성 (공개/비공개, 200자 제한)"""
    model = Journal
    form_class = JournalForm
    template_name = 'homecook/journal_form.html'
    success_url = reverse_lazy('homecook:my_challenge')
    login_url = '/admin/login/'
    
    def form_valid(self, form):
        form.instance.user = self.request.user
        visibility_text = '공개' if form.instance.visibility == 'public' else '비공개'
        messages.success(self.request, f'기록이 성공적으로 저장되었습니다! ({visibility_text}) 📔')
        return super().form_valid(form)
    
    def form_invalid(self, form):
        messages.error(self.request, '기록 저장에 실패했습니다.')
        return super().form_invalid(form)


# ============= 나중에 구현할 UPDATE, DELETE 뷰들 =============

class HomecookFoodImageUpdateView(LoginRequiredMixin, generic.UpdateView):
    """음식 이미지 수정"""
    pass


class HomecookFoodImageDeleteView(LoginRequiredMixin, generic.DeleteView):
    """음식 이미지 삭제"""
    pass


class HomecookReceiptUpdateView(LoginRequiredMixin, generic.UpdateView):
    """영수증 수정"""
    pass


class HomecookReceiptDeleteView(LoginRequiredMixin, generic.DeleteView):
    """영수증 삭제"""
    pass


class HomecookRecipeUpdateView(LoginRequiredMixin, generic.UpdateView):
    """레시피 수정"""
    pass


class HomecookRecipeDeleteView(LoginRequiredMixin, generic.DeleteView):
    """레시피 삭제"""
    pass


class HomecookJournalUpdateView(LoginRequiredMixin, generic.UpdateView):
    """기록장 수정"""
    pass


class HomecookJournalDeleteView(LoginRequiredMixin, generic.DeleteView):
    """기록장 삭제"""
    pass