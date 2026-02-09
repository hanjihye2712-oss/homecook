from django.http import HttpResponse, Http404, JsonResponse
from django.views import generic
from django.contrib.auth.mixins import LoginRequiredMixin
from django.db.models import Q, F
from django.urls import reverse_lazy, reverse
from django.contrib import messages
from django.shortcuts import get_object_or_404, redirect
from django.views.decorators.http import require_POST
from django.contrib.auth.decorators import login_required
from .models import FoodImage, Receipt, Recipe, Journal, ChallengeSet
from .forms import FoodImageForm, ReceiptForm, RecipeForm, JournalForm, ChallengeSetCreateForm
from accounts.models import UserProfile
import pytesseract
from PIL import Image as PILImage
import os
import logging

# 로거 설정
logger = logging.getLogger(__name__)

# 상수 정의
RECOMMENDED_IMAGE_WIDTH = 1000
RECOMMENDED_IMAGE_HEIGHT = 1000


# ============================================================================
# 유틸리티 함수들. 
# ============================================================================

def process_ocr(receipt):
    """
    영수증 OCR 처리 헬퍼 함수
    
    Args:
        receipt: Receipt 모델 인스턴스
    
    Returns:
        tuple: (success: bool, error_message: str or None)
    """
    try:
        img = PILImage.open(receipt.image.path)
        ocr_text = pytesseract.image_to_string(img, lang='kor+eng')
        receipt.ocr_text = ocr_text.strip()
        receipt.is_processed = True
        receipt.save()
        return True, None
    except FileNotFoundError as e:
        logger.error(f"OCR 처리 실패 - 파일을 찾을 수 없음: {e}")
        return False, "영수증 이미지 파일을 찾을 수 없습니다."
    except Exception as e:
        logger.error(f"OCR 처리 실패: {e}")
        return False, f"OCR 처리 중 오류가 발생했습니다: {str(e)}"


def check_image_resolution(image_file):
    """
    이미지 해상도 체크 헬퍼 함수
    
    Args:
        image_file: 이미지 파일 객체
    
    Returns:
        tuple: (is_recommended: bool, width: int, height: int)
    """
    try:
        img = PILImage.open(image_file)
        is_recommended = (img.width == RECOMMENDED_IMAGE_WIDTH and 
                         img.height == RECOMMENDED_IMAGE_HEIGHT)
        return is_recommended, img.width, img.height
    except Exception as e:
        logger.error(f"이미지 해상도 체크 실패: {e}")
        return False, 0, 0


def delete_file_safely(file_field):
    """
    파일 안전 삭제 헬퍼 함수
    
    Args:
        file_field: Django FileField/ImageField
    
    Returns:
        bool: 삭제 성공 여부
    """
    try:
        if file_field and os.path.isfile(file_field.path):
            os.remove(file_field.path)
            logger.info(f"파일 삭제 성공: {file_field.path}")
            return True
    except Exception as e:
        logger.error(f"파일 삭제 실패: {e}")
    return False


# ============================================================================
# Mixins
# ============================================================================

class UserFilterMixin:
    """사용자별 데이터 필터링을 위한 Mixin"""
    
    def get_queryset(self):
        return super().get_queryset().filter(user=self.request.user)


class SuccessMessageMixin:
    """성공 메시지를 위한 Mixin"""
    success_message = ""
    
    def form_valid(self, form):
        response = super().form_valid(form)
        if self.success_message:
            messages.success(self.request, self.success_message)
        return response
    
    def form_invalid(self, form):
        messages.error(self.request, '처리 중 오류가 발생했습니다.')
        return super().form_invalid(form)


class DeleteMessageMixin:
    """삭제 메시지를 위한 Mixin"""
    delete_message = ""
    
    def delete(self, request, *args, **kwargs):
        if self.delete_message:
            messages.success(self.request, self.delete_message)
        return super().delete(request, *args, **kwargs)


# ============================================================================
# 메인 인덱스 페이지 (2x2 카테고리 그리드)
# ============================================================================

class MainIndexView(generic.TemplateView):
    """메인 페이지 - 4가지 카테고리 그리드"""
    template_name = 'main_index.html'


# ============================================================================
# 카테고리별 플레이스홀더 페이지
# ============================================================================

class WalkingView(generic.TemplateView):
    """오늘의 Walking 페이지"""
    template_name = 'homecook/walking.html'


class WeightView(generic.TemplateView):
    """오늘의 Weight 페이지"""
    template_name = 'homecook/weight.html'


class HealingView(generic.TemplateView):
    """오늘의 Healing 페이지"""
    template_name = 'homecook/healing.html'


# ============================================================================
# 랜딩 페이지 (홈쿡)
# ============================================================================

class HomecookLandingView(generic.ListView):
    """홈쿡 랜딩 페이지 - 다른 사람들의 최근 음식 사진 8개 표시"""
    template_name = 'homecook/landing.html'
    context_object_name = 'recent_food_images'

    def get_queryset(self):
        """모든 사용자의 최근 음식 사진 30개 (3개 x 10줄)"""
        return FoodImage.objects.all()[:30]


# ============================================================================
# 챌린지 세트 관련 Views
# ============================================================================

class HomecookMyChallengeView(LoginRequiredMixin, generic.ListView):
    """My Challenge 페이지 - 챌린지 세트 단위로 표시"""
    model = ChallengeSet
    template_name = 'homecook/my_challenge.html'
    context_object_name = 'challenge_sets'
    login_url = '/admin/login/'
    paginate_by = 10
    
    def get_queryset(self):
        """로그인한 사용자의 챌린지 세트"""
        queryset = ChallengeSet.objects.filter(
            user=self.request.user
        ).select_related('food_image', 'receipt', 'recipe', 'journal')
        
        # 검색 필터
        search_query = self.request.GET.get('search', '')
        if search_query:
            queryset = queryset.filter(
                Q(title__icontains=search_query) |
                Q(food_image__title__icontains=search_query) |
                Q(recipe__title__icontains=search_query) |
                Q(recipe__content__icontains=search_query) |
                Q(journal__title__icontains=search_query) |
                Q(journal__content__icontains=search_query)
            )
        
        # 정렬
        sort = self.request.GET.get('sort', 'latest')
        order_by = 'created_at' if sort == 'oldest' else '-created_at'
        queryset = queryset.order_by(order_by)
        
        return queryset
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['search_query'] = self.request.GET.get('search', '')
        context['sort'] = self.request.GET.get('sort', 'latest')
        return context


class HomecookChallengeSetCreateView(LoginRequiredMixin, generic.FormView):
    """통합 챌린지 세트 생성 - 모든 항목을 한 번에 입력"""
    form_class = ChallengeSetCreateForm
    template_name = 'homecook/challenge_set_create_all.html'
    login_url = '/admin/login/'
    
    def form_valid(self, form):
        # 1. 챌린지 세트 생성
        challenge_set = ChallengeSet.objects.create(
            user=self.request.user,
            title=form.cleaned_data['set_title']
        )
        
        # 2. 음식 이미지 추가 (선택사항)
        self._add_food_image(form, challenge_set)
        
        # 3. 영수증 추가 (선택사항)
        self._add_receipt(form, challenge_set)
        
        # 4. 레시피 추가 (선택사항)
        self._add_recipe(form, challenge_set)
        
        # 5. 기록장 추가 (선택사항)
        self._add_journal(form, challenge_set)
        
        # 6. 포인트 100P 적립
        profile, _ = UserProfile.objects.get_or_create(user=self.request.user)
        profile.points += 100
        profile.save(update_fields=['points'])

        messages.success(self.request, '챌린지 세트가 성공적으로 생성되었습니다! 100P가 적립되었습니다! 🎉')
        return redirect('homecook:my_challenge')
    
    def _add_food_image(self, form, challenge_set):
        """음식 이미지 추가 헬퍼 메서드"""
        if not form.cleaned_data.get('food_image'):
            return
        
        food_image = FoodImage.objects.create(
            user=self.request.user,
            challenge_set=challenge_set,
            image=form.cleaned_data['food_image'],
            title=form.cleaned_data.get('food_image_title', '')
        )
        
        # 해상도 체크
        is_recommended, width, height = check_image_resolution(food_image.image)
        if not is_recommended:
            messages.warning(
                self.request,
                f'권장 해상도는 {RECOMMENDED_IMAGE_WIDTH}x{RECOMMENDED_IMAGE_HEIGHT}입니다. '
                f'(현재: {width}x{height}px)'
            )
    
    def _add_receipt(self, form, challenge_set):
        """영수증 추가 헬퍼 메서드"""
        if not form.cleaned_data.get('receipt_image'):
            return
        
        receipt = Receipt.objects.create(
            user=self.request.user,
            challenge_set=challenge_set,
            image=form.cleaned_data['receipt_image']
        )
        
        # OCR 처리
        success, error_msg = process_ocr(receipt)
        if not success:
            messages.warning(self.request, f'OCR 처리 실패: {error_msg}')
    
    def _add_recipe(self, form, challenge_set):
        """레시피 추가 헬퍼 메서드"""
        if form.cleaned_data.get('recipe_title') and form.cleaned_data.get('recipe_content'):
            Recipe.objects.create(
                user=self.request.user,
                challenge_set=challenge_set,
                title=form.cleaned_data['recipe_title'],
                content=form.cleaned_data['recipe_content']
            )
    
    def _add_journal(self, form, challenge_set):
        """기록장 추가 헬퍼 메서드"""
        if form.cleaned_data.get('journal_title') and form.cleaned_data.get('journal_content'):
            Journal.objects.create(
                user=self.request.user,
                challenge_set=challenge_set,
                title=form.cleaned_data['journal_title'],
                content=form.cleaned_data['journal_content'],
                visibility=form.cleaned_data.get('journal_visibility', 'private')
            )


class HomecookChallengeSetEditView(LoginRequiredMixin, UserFilterMixin, generic.DetailView):
    """챌린지 세트 편집 페이지"""
    model = ChallengeSet
    template_name = 'homecook/challenge_set_edit.html'
    context_object_name = 'challenge_set'
    login_url = '/admin/login/'
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['food_image_form'] = FoodImageForm()
        context['receipt_form'] = ReceiptForm()
        context['recipe_form'] = RecipeForm()
        context['journal_form'] = JournalForm()
        return context


@login_required
@require_POST
def update_challenge_set_title(request, pk):
    """챌린지 세트 제목 수정"""
    challenge_set = get_object_or_404(ChallengeSet, pk=pk, user=request.user)
    new_title = request.POST.get('title', '').strip()
    if new_title:
        challenge_set.title = new_title
        challenge_set.save(update_fields=['title'])
    return redirect('homecook:challenge_set_edit', pk=pk)


class HomecookChallengeSetDeleteView(LoginRequiredMixin, UserFilterMixin,
                                     DeleteMessageMixin, generic.DeleteView):
    """챌린지 세트 삭제"""
    model = ChallengeSet
    template_name = 'homecook/challenge_set_confirm_delete.html'
    success_url = reverse_lazy('homecook:my_challenge')
    login_url = '/admin/login/'
    delete_message = '챌린지 세트가 삭제되었습니다. 🗑️'
    
    def delete(self, request, *args, **kwargs):
        self.object = self.get_object()

        # 관련 파일들 삭제
        if hasattr(self.object, 'food_image') and self.object.food_image:
            delete_file_safely(self.object.food_image.image)

        if hasattr(self.object, 'receipt') and self.object.receipt:
            delete_file_safely(self.object.receipt.image)

        # 포인트 100P 차감
        profile, _ = UserProfile.objects.get_or_create(user=request.user)
        profile.points = max(0, profile.points - 100)
        profile.save(update_fields=['points'])

        return super().delete(request, *args, **kwargs)


# ============================================================================
# 챌린지 세트에 항목 추가하는 함수들
# ============================================================================

@login_required
@require_POST
def add_food_image_to_set(request, set_pk):
    """챌린지 세트에 음식 이미지 추가"""
    challenge_set = get_object_or_404(ChallengeSet, pk=set_pk, user=request.user)
    
    form = FoodImageForm(request.POST, request.FILES)
    if form.is_valid():
        food_image = form.save(commit=False)
        food_image.user = request.user
        food_image.challenge_set = challenge_set
        food_image.save()
        
        # 해상도 체크
        is_recommended, width, height = check_image_resolution(food_image.image)
        if not is_recommended:
            messages.warning(
                request,
                f'권장 해상도는 {RECOMMENDED_IMAGE_WIDTH}x{RECOMMENDED_IMAGE_HEIGHT}입니다. '
                f'(현재: {width}x{height}px)'
            )
        
        messages.success(request, '음식 이미지가 추가되었습니다! 🍽️')
    else:
        messages.error(request, '이미지 추가에 실패했습니다.')
    
    return redirect('homecook:challenge_set_edit', pk=set_pk)


@login_required
@require_POST
def add_receipt_to_set(request, set_pk):
    """챌린지 세트에 영수증 추가"""
    challenge_set = get_object_or_404(ChallengeSet, pk=set_pk, user=request.user)
    
    form = ReceiptForm(request.POST, request.FILES)
    if form.is_valid():
        receipt = form.save(commit=False)
        receipt.user = request.user
        receipt.challenge_set = challenge_set
        receipt.save()
        
        # OCR 처리
        success, error_msg = process_ocr(receipt)
        if success:
            messages.success(request, '영수증이 추가되고 OCR이 완료되었습니다! 🧾')
        else:
            messages.warning(request, f'영수증은 추가되었으나 OCR 실패: {error_msg}')
    else:
        messages.error(request, '영수증 추가에 실패했습니다.')
    
    return redirect('homecook:challenge_set_edit', pk=set_pk)


@login_required
@require_POST
def add_recipe_to_set(request, set_pk):
    """챌린지 세트에 레시피 추가"""
    challenge_set = get_object_or_404(ChallengeSet, pk=set_pk, user=request.user)
    
    form = RecipeForm(request.POST)
    if form.is_valid():
        recipe = form.save(commit=False)
        recipe.user = request.user
        recipe.challenge_set = challenge_set
        recipe.save()
        messages.success(request, '레시피가 추가되었습니다! 👨‍🍳')
    else:
        messages.error(request, '레시피 추가에 실패했습니다.')
    
    return redirect('homecook:challenge_set_edit', pk=set_pk)


@login_required
@require_POST
def add_journal_to_set(request, set_pk):
    """챌린지 세트에 기록장 추가"""
    challenge_set = get_object_or_404(ChallengeSet, pk=set_pk, user=request.user)
    
    form = JournalForm(request.POST)
    if form.is_valid():
        journal = form.save(commit=False)
        journal.user = request.user
        journal.challenge_set = challenge_set
        journal.save()
        
        visibility_text = '공개' if journal.visibility == 'public' else '비공개'
        messages.success(request, f'기록장이 추가되었습니다! ({visibility_text}) 📔')
    else:
        messages.error(request, '기록장 추가에 실패했습니다.')
    
    return redirect('homecook:challenge_set_edit', pk=set_pk)


# ============================================================================
# 상세보기 Views
# ============================================================================

class HomecookFoodImageDetailView(LoginRequiredMixin, UserFilterMixin, generic.DetailView):
    """음식 이미지 상세보기"""
    model = FoodImage
    template_name = 'homecook/food_image_detail.html'
    context_object_name = 'food_image'
    login_url = '/admin/login/'


class HomecookReceiptDetailView(LoginRequiredMixin, UserFilterMixin, generic.DetailView):
    """영수증 상세보기"""
    model = Receipt
    template_name = 'homecook/receipt_detail.html'
    context_object_name = 'receipt'
    login_url = '/admin/login/'


class HomecookRecipeDetailView(generic.DetailView):
    """레시피 상세보기"""
    model = Recipe
    template_name = 'homecook/recipe_detail.html'
    context_object_name = 'recipe'
    
    def get_object(self, queryset=None):
        obj = super().get_object(queryset)
        # 조회수 증가
        Recipe.objects.filter(pk=obj.pk).update(views=F('views') + 1)
        obj.refresh_from_db()
        return obj


class HomecookJournalDetailView(generic.DetailView):
    """기록장 상세보기"""
    model = Journal
    template_name = 'homecook/journal_detail.html'
    context_object_name = 'journal'
    
    def get_object(self, queryset=None):
        obj = super().get_object(queryset)
        
        # 공개 기록장이면 누구나 접근 가능
        if obj.visibility == Journal.PUBLIC:
            return obj
        
        # 비공개 기록장은 작성자만 접근 가능
        if self.request.user.is_authenticated and obj.user == self.request.user:
            return obj
        
        raise Http404("접근 권한이 없습니다.")


# ============================================================================
# 수정 Views
# ============================================================================

class HomecookFoodImageUpdateView(LoginRequiredMixin, UserFilterMixin, 
                                  SuccessMessageMixin, generic.UpdateView):
    """음식 이미지 수정"""
    model = FoodImage
    form_class = FoodImageForm
    template_name = 'homecook/food_image_form.html'
    login_url = '/admin/login/'
    success_message = '음식 이미지가 성공적으로 수정되었습니다! ✏️'
    
    def get_success_url(self):
        return reverse('homecook:food_image_detail', kwargs={'pk': self.object.pk})


class HomecookReceiptUpdateView(LoginRequiredMixin, UserFilterMixin, generic.UpdateView):
    """영수증 수정"""
    model = Receipt
    form_class = ReceiptForm
    template_name = 'homecook/receipt_form.html'
    login_url = '/admin/login/'
    
    def get_success_url(self):
        return reverse('homecook:receipt_detail', kwargs={'pk': self.object.pk})
    
    def form_valid(self, form):
        # 이미지가 변경된 경우 OCR 재처리
        if 'image' in form.changed_data:
            response = super().form_valid(form)
            success, error_msg = process_ocr(self.object)
            
            if success:
                messages.success(self.request, '영수증이 수정되고 OCR이 재처리되었습니다! ✏️')
            else:
                messages.warning(self.request, f'수정되었으나 OCR 재처리 중 오류: {error_msg}')
            
            return response
        else:
            messages.success(self.request, '영수증이 성공적으로 수정되었습니다! ✏️')
            return super().form_valid(form)
    
    def form_invalid(self, form):
        messages.error(self.request, '수정에 실패했습니다.')
        return super().form_invalid(form)


class HomecookRecipeUpdateView(LoginRequiredMixin, UserFilterMixin, 
                               SuccessMessageMixin, generic.UpdateView):
    """레시피 수정"""
    model = Recipe
    form_class = RecipeForm
    template_name = 'homecook/recipe_form.html'
    login_url = '/admin/login/'
    success_message = '레시피가 성공적으로 수정되었습니다! ✏️'
    
    def get_success_url(self):
        return reverse('homecook:recipe_detail', kwargs={'pk': self.object.pk})


class HomecookJournalUpdateView(LoginRequiredMixin, UserFilterMixin, generic.UpdateView):
    """기록장 수정"""
    model = Journal
    form_class = JournalForm
    template_name = 'homecook/journal_form.html'
    login_url = '/admin/login/'
    
    def get_success_url(self):
        return reverse('homecook:journal_detail', kwargs={'pk': self.object.pk})
    
    def form_valid(self, form):
        visibility_text = '공개' if form.instance.visibility == 'public' else '비공개'
        messages.success(self.request, f'기록이 성공적으로 수정되었습니다! ({visibility_text}) ✏️')
        return super().form_valid(form)
    
    def form_invalid(self, form):
        messages.error(self.request, '수정에 실패했습니다.')
        return super().form_invalid(form)


# ============================================================================
# 삭제 Views
# ============================================================================

class HomecookFoodImageDeleteView(LoginRequiredMixin, UserFilterMixin, 
                                  DeleteMessageMixin, generic.DeleteView):
    """음식 이미지 삭제"""
    model = FoodImage
    template_name = 'homecook/food_image_confirm_delete.html'
    success_url = reverse_lazy('homecook:my_challenge')
    login_url = '/admin/login/'
    delete_message = '음식 이미지가 삭제되었습니다. 🗑️'
    
    def delete(self, request, *args, **kwargs):
        self.object = self.get_object()
        delete_file_safely(self.object.image)
        return super().delete(request, *args, **kwargs)


class HomecookReceiptDeleteView(LoginRequiredMixin, UserFilterMixin, 
                                DeleteMessageMixin, generic.DeleteView):
    """영수증 삭제"""
    model = Receipt
    template_name = 'homecook/receipt_confirm_delete.html'
    success_url = reverse_lazy('homecook:my_challenge')
    login_url = '/admin/login/'
    delete_message = '영수증이 삭제되었습니다. 🗑️'
    
    def delete(self, request, *args, **kwargs):
        self.object = self.get_object()
        delete_file_safely(self.object.image)
        return super().delete(request, *args, **kwargs)


class HomecookRecipeDeleteView(LoginRequiredMixin, UserFilterMixin, 
                               DeleteMessageMixin, generic.DeleteView):
    """레시피 삭제"""
    model = Recipe
    template_name = 'homecook/recipe_confirm_delete.html'
    success_url = reverse_lazy('homecook:my_challenge')
    login_url = '/admin/login/'
    delete_message = '레시피가 삭제되었습니다. 🗑️'


class HomecookJournalDeleteView(LoginRequiredMixin, UserFilterMixin, 
                                DeleteMessageMixin, generic.DeleteView):
    """기록장 삭제"""
    model = Journal
    template_name = 'homecook/journal_confirm_delete.html'
    success_url = reverse_lazy('homecook:my_challenge')
    login_url = '/admin/login/'
    delete_message = '기록이 삭제되었습니다. 🗑️'


# ============================================================================
# 기타 기능 함수들
# ============================================================================

@login_required
@require_POST
def recipe_like_toggle(request, pk):
    """레시피 좋아요 토글"""
    recipe = get_object_or_404(Recipe, pk=pk)
    
    if request.user in recipe.likes.all():
        recipe.likes.remove(request.user)
        liked = False
    else:
        recipe.likes.add(request.user)
        liked = True
    
    return JsonResponse({
        'liked': liked,
        'total_likes': recipe.total_likes()
    })
