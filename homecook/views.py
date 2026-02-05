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
import pytesseract
from PIL import Image as PILImage
import os


class HomecookLandingView(generic.ListView):
    """홈쿡 랜딩 페이지 - 다른 사람들의 최근 음식 사진 8개 표시"""
    template_name = 'homecook/landing.html'
    context_object_name = 'recent_food_images'
    
    def get_queryset(self):
        """모든 사용자의 최근 음식 사진 8개"""
        return FoodImage.objects.all()[:8]


class HomecookMyChallengeView(LoginRequiredMixin, generic.ListView):
    """My Challenge 페이지 - 챌린지 세트 단위로 표시"""
    model = ChallengeSet
    template_name = 'homecook/my_challenge.html'
    context_object_name = 'challenge_sets'
    login_url = '/admin/login/'
    paginate_by = 10
    
    def get_queryset(self):
        """로그인한 사용자의 챌린지 세트"""
        queryset = ChallengeSet.objects.filter(user=self.request.user).select_related(
            'food_image', 'receipt', 'recipe', 'journal'
        )
        
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
        
        sort = self.request.GET.get('sort', 'latest')
        if sort == 'oldest':
            queryset = queryset.order_by('created_at')
        else:
            queryset = queryset.order_by('-created_at')
        
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
        if form.cleaned_data.get('food_image'):
            food_image = FoodImage.objects.create(
                user=self.request.user,
                challenge_set=challenge_set,
                image=form.cleaned_data['food_image'],
                title=form.cleaned_data.get('food_image_title', '')
            )
           # 해상도 체크
            img = PILImage.open(food_image.image)
            if img.width != 1000 or img.height != 1000:
                messages.warning(
                    self.request,
                    f'권장 해상도는 1000x1000입니다. (현재: {img.width}x{img.height}px)'
                )
        
        # 3. 영수증 추가 (선택사항)
        if form.cleaned_data.get('receipt_image'):
            receipt = Receipt.objects.create(
                user=self.request.user,
                challenge_set=challenge_set,
                image=form.cleaned_data['receipt_image']
            )
            # OCR 처리
            try:
                img = PILImage.open(receipt.image.path)
                ocr_text = pytesseract.image_to_string(img, lang='kor+eng')
                receipt.ocr_text = ocr_text.strip()
                receipt.is_processed = True
                receipt.save()
            except Exception as e:
                messages.warning(self.request, f'OCR 처리 실패: {str(e)}')
        
        # 4. 레시피 추가 (선택사항)
        if form.cleaned_data.get('recipe_title') and form.cleaned_data.get('recipe_content'):
            Recipe.objects.create(
                user=self.request.user,
                challenge_set=challenge_set,
                title=form.cleaned_data['recipe_title'],
                content=form.cleaned_data['recipe_content']
            )
        # 5. 기록장 추가 (선택사항)
        if form.cleaned_data.get('journal_title') and form.cleaned_data.get('journal_content'):
            Journal.objects.create(
                user=self.request.user,
                challenge_set=challenge_set,
                title=form.cleaned_data['journal_title'],
                content=form.cleaned_data['journal_content'],
                visibility=form.cleaned_data.get('journal_visibility', 'private')
            )
        
        messages.success(self.request, '챌린지 세트가 성공적으로 생성되었습니다! 🎉')
        return redirect('homecook:my_challenge')
    





class HomecookChallengeSetEditView(LoginRequiredMixin, generic.DetailView):
    """챌린지 세트 편집 페이지"""
    model = ChallengeSet
    template_name = 'homecook/challenge_set_edit.html'
    context_object_name = 'challenge_set'
    login_url = '/admin/login/'
    
    def get_queryset(self):
        return ChallengeSet.objects.filter(user=self.request.user)
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['food_image_form'] = FoodImageForm()
        context['receipt_form'] = ReceiptForm()
        context['recipe_form'] = RecipeForm()
        context['journal_form'] = JournalForm()
        return context


class HomecookChallengeSetDeleteView(LoginRequiredMixin, generic.DeleteView):
    """챌린지 세트 삭제"""
    model = ChallengeSet
    template_name = 'homecook/challenge_set_confirm_delete.html'
    success_url = reverse_lazy('homecook:my_challenge')
    login_url = '/admin/login/'
    
    def get_queryset(self):
        return ChallengeSet.objects.filter(user=self.request.user)
    
    def delete(self, request, *args, **kwargs):
        self.object = self.get_object()
        
        if hasattr(self.object, 'food_image') and self.object.food_image:
            if self.object.food_image.image and os.path.isfile(self.object.food_image.image.path):
                os.remove(self.object.food_image.image.path)
        
        if hasattr(self.object, 'receipt') and self.object.receipt:
            if self.object.receipt.image and os.path.isfile(self.object.receipt.image.path):
                os.remove(self.object.receipt.image.path)
        
        messages.success(self.request, '챌린지 세트가 삭제되었습니다. 🗑️')
        return super().delete(request, *args, **kwargs)


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
        
        img = PILImage.open(food_image.image)
        if img.width != 1000 or img.height != 1000:
            messages.warning(
                request,
                f'권장 해상도는 1000x1000입니다. (현재: {img.width}x{img.height}px)'
            )
        
        food_image.save()
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
        
        try:
            img = PILImage.open(receipt.image.path)
            ocr_text = pytesseract.image_to_string(img, lang='kor+eng')
            receipt.ocr_text = ocr_text.strip()
            receipt.is_processed = True
            receipt.save()
            messages.success(request, '영수증이 추가되고 OCR이 완료되었습니다! 🧾')
        except Exception as e:
            messages.warning(request, f'영수증은 추가되었으나 OCR 실패: {str(e)}')
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


class HomecookFoodImageDetailView(LoginRequiredMixin, generic.DetailView):
    """음식 이미지 상세보기"""
    model = FoodImage
    template_name = 'homecook/food_image_detail.html'
    context_object_name = 'food_image'
    login_url = '/admin/login/'
    
    def get_queryset(self):
        return FoodImage.objects.filter(user=self.request.user)


class HomecookReceiptDetailView(LoginRequiredMixin, generic.DetailView):
    """영수증 상세보기"""
    model = Receipt
    template_name = 'homecook/receipt_detail.html'
    context_object_name = 'receipt'
    login_url = '/admin/login/'
    
    def get_queryset(self):
        return Receipt.objects.filter(user=self.request.user)


class HomecookRecipeDetailView(generic.DetailView):
    """레시피 상세보기"""
    model = Recipe
    template_name = 'homecook/recipe_detail.html'
    context_object_name = 'recipe'
    
    def get_object(self, queryset=None):
        obj = super().get_object(queryset)
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
        
        if obj.visibility == Journal.PUBLIC:
            return obj
        
        if self.request.user.is_authenticated and obj.user == self.request.user:
            return obj
        
        raise Http404("접근 권한이 없습니다.")


class HomecookFoodImageUpdateView(LoginRequiredMixin, generic.UpdateView):
    """음식 이미지 수정"""
    model = FoodImage
    form_class = FoodImageForm
    template_name = 'homecook/food_image_form.html'
    login_url = '/admin/login/'
    
    def get_queryset(self):
        return FoodImage.objects.filter(user=self.request.user)
    
    def get_success_url(self):
        return reverse('homecook:food_image_detail', kwargs={'pk': self.object.pk})
    
    def form_valid(self, form):
        messages.success(self.request, '음식 이미지가 성공적으로 수정되었습니다! ✏️')
        return super().form_valid(form)
    
    def form_invalid(self, form):
        messages.error(self.request, '수정에 실패했습니다.')
        return super().form_invalid(form)


class HomecookReceiptUpdateView(LoginRequiredMixin, generic.UpdateView):
    """영수증 수정"""
    model = Receipt
    form_class = ReceiptForm
    template_name = 'homecook/receipt_form.html'
    login_url = '/admin/login/'
    
    def get_queryset(self):
        return Receipt.objects.filter(user=self.request.user)
    
    def get_success_url(self):
        return reverse('homecook:receipt_detail', kwargs={'pk': self.object.pk})
    
    def form_valid(self, form):
        if 'image' in form.changed_data:
            response = super().form_valid(form)
            try:
                receipt = self.object
                img = PILImage.open(receipt.image.path)
                ocr_text = pytesseract.image_to_string(img, lang='kor+eng')
                receipt.ocr_text = ocr_text.strip()
                receipt.is_processed = True
                receipt.save()
                messages.success(self.request, '영수증이 수정되고 OCR이 재처리되었습니다! ✏️')
            except Exception as e:
                messages.warning(self.request, f'수정되었으나 OCR 재처리 중 오류: {str(e)}')
            return response
        else:
            messages.success(self.request, '영수증이 성공적으로 수정되었습니다! ✏️')
            return super().form_valid(form)
    
    def form_invalid(self, form):
        messages.error(self.request, '수정에 실패했습니다.')
        return super().form_invalid(form)


class HomecookRecipeUpdateView(LoginRequiredMixin, generic.UpdateView):
    """레시피 수정"""
    model = Recipe
    form_class = RecipeForm
    template_name = 'homecook/recipe_form.html'
    login_url = '/admin/login/'
    
    def get_queryset(self):
        return Recipe.objects.filter(user=self.request.user)
    
    def get_success_url(self):
        return reverse('homecook:recipe_detail', kwargs={'pk': self.object.pk})
    
    def form_valid(self, form):
        messages.success(self.request, '레시피가 성공적으로 수정되었습니다! ✏️')
        return super().form_valid(form)
    
    def form_invalid(self, form):
        messages.error(self.request, '수정에 실패했습니다.')
        return super().form_invalid(form)


class HomecookJournalUpdateView(LoginRequiredMixin, generic.UpdateView):
    """기록장 수정"""
    model = Journal
    form_class = JournalForm
    template_name = 'homecook/journal_form.html'
    login_url = '/admin/login/'
    
    def get_queryset(self):
        return Journal.objects.filter(user=self.request.user)
    
    def get_success_url(self):
        return reverse('homecook:journal_detail', kwargs={'pk': self.object.pk})
    
    def form_valid(self, form):
        visibility_text = '공개' if form.instance.visibility == 'public' else '비공개'
        messages.success(self.request, f'기록이 성공적으로 수정되었습니다! ({visibility_text}) ✏️')
        return super().form_valid(form)
    
    def form_invalid(self, form):
        messages.error(self.request, '수정에 실패했습니다.')
        return super().form_invalid(form)


class HomecookFoodImageDeleteView(LoginRequiredMixin, generic.DeleteView):
    """음식 이미지 삭제"""
    model = FoodImage
    template_name = 'homecook/food_image_confirm_delete.html'
    success_url = reverse_lazy('homecook:my_challenge')
    login_url = '/admin/login/'
    
    def get_queryset(self):
        return FoodImage.objects.filter(user=self.request.user)
    
    def delete(self, request, *args, **kwargs):
        self.object = self.get_object()
        
        if self.object.image:
            if os.path.isfile(self.object.image.path):
                os.remove(self.object.image.path)
        
        messages.success(self.request, '음식 이미지가 삭제되었습니다. 🗑️')
        return super().delete(request, *args, **kwargs)


class HomecookReceiptDeleteView(LoginRequiredMixin, generic.DeleteView):
    """영수증 삭제"""
    model = Receipt
    template_name = 'homecook/receipt_confirm_delete.html'
    success_url = reverse_lazy('homecook:my_challenge')
    login_url = '/admin/login/'
    
    def get_queryset(self):
        return Receipt.objects.filter(user=self.request.user)
    
    def delete(self, request, *args, **kwargs):
        self.object = self.get_object()
        
        if self.object.image:
            if os.path.isfile(self.object.image.path):
                os.remove(self.object.image.path)
        
        messages.success(self.request, '영수증이 삭제되었습니다. 🗑️')
        return super().delete(request, *args, **kwargs)


class HomecookRecipeDeleteView(LoginRequiredMixin, generic.DeleteView):
    """레시피 삭제"""
    model = Recipe
    template_name = 'homecook/recipe_confirm_delete.html'
    success_url = reverse_lazy('homecook:my_challenge')
    login_url = '/admin/login/'
    
    def get_queryset(self):
        return Recipe.objects.filter(user=self.request.user)
    
    def delete(self, request, *args, **kwargs):
        messages.success(self.request, '레시피가 삭제되었습니다. 🗑️')
        return super().delete(request, *args, **kwargs)


class HomecookJournalDeleteView(LoginRequiredMixin, generic.DeleteView):
    """기록장 삭제"""
    model = Journal
    template_name = 'homecook/journal_confirm_delete.html'
    success_url = reverse_lazy('homecook:my_challenge')
    login_url = '/admin/login/'
    
    def get_queryset(self):
        return Journal.objects.filter(user=self.request.user)
    
    def delete(self, request, *args, **kwargs):
        messages.success(self.request, '기록이 삭제되었습니다. 🗑️')
        return super().delete(request, *args, **kwargs)


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