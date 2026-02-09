from django.urls import path
from . import views

app_name = 'homecook'

urlpatterns = [
    # 메인 인덱스 페이지 (2x2 카테고리 그리드)
    path('', views.MainIndexView.as_view(), name='main_index'),

    # 카테고리별 페이지
    path('walking/', views.WalkingView.as_view(), name='walking'),
    path('weight/', views.WeightView.as_view(), name='weight'),
    path('landing/', views.HomecookLandingView.as_view(), name='landing'),
    path('healing/', views.HealingView.as_view(), name='healing'),

    # My Challenge 페이지 (세트 기반)
    path('my-challenge/', views.HomecookMyChallengeView.as_view(), name='my_challenge'),
    
    # 챌린지 세트 관리 (새로 추가)
    path('challenge-set/create/', views.HomecookChallengeSetCreateView.as_view(), name='challenge_set_create'),
    path('challenge-set/<int:pk>/edit/', views.HomecookChallengeSetEditView.as_view(), name='challenge_set_edit'),
    path('challenge-set/<int:pk>/delete/', views.HomecookChallengeSetDeleteView.as_view(), name='challenge_set_delete'),
    path('challenge-set/<int:pk>/update-title/', views.update_challenge_set_title, name='challenge_set_update_title'),

    # 챌린지 세트에 항목 추가 (새로 추가)
    path('challenge-set/<int:set_pk>/add-food-image/', views.add_food_image_to_set, name='add_food_image_to_set'),
    path('challenge-set/<int:set_pk>/add-receipt/', views.add_receipt_to_set, name='add_receipt_to_set'),
    path('challenge-set/<int:set_pk>/add-recipe/', views.add_recipe_to_set, name='add_recipe_to_set'),
    path('challenge-set/<int:set_pk>/add-journal/', views.add_journal_to_set, name='add_journal_to_set'),
    
    # Detail Views (유지)
    path('food-image/<int:pk>/', views.HomecookFoodImageDetailView.as_view(), name='food_image_detail'),
    path('receipt/<int:pk>/', views.HomecookReceiptDetailView.as_view(), name='receipt_detail'),
    path('recipe/<int:pk>/', views.HomecookRecipeDetailView.as_view(), name='recipe_detail'),
    path('journal/<int:pk>/', views.HomecookJournalDetailView.as_view(), name='journal_detail'),
    
    # Update Views (유지 - Detail 페이지에서 필요!)
    path('food-image/<int:pk>/update/', views.HomecookFoodImageUpdateView.as_view(), name='food_image_update'),
    path('receipt/<int:pk>/update/', views.HomecookReceiptUpdateView.as_view(), name='receipt_update'),
    path('recipe/<int:pk>/update/', views.HomecookRecipeUpdateView.as_view(), name='recipe_update'),
    path('journal/<int:pk>/update/', views.HomecookJournalUpdateView.as_view(), name='journal_update'),
    
    # Delete Views (유지 - Detail 페이지에서 필요!)
    path('food-image/<int:pk>/delete/', views.HomecookFoodImageDeleteView.as_view(), name='food_image_delete'),
    path('receipt/<int:pk>/delete/', views.HomecookReceiptDeleteView.as_view(), name='receipt_delete'),
    path('recipe/<int:pk>/delete/', views.HomecookRecipeDeleteView.as_view(), name='recipe_delete'),
    path('journal/<int:pk>/delete/', views.HomecookJournalDeleteView.as_view(), name='journal_delete'),
    
    # 좋아요 기능 (유지)
    path('recipe/<int:pk>/like/', views.recipe_like_toggle, name='recipe_like_toggle'),
]
