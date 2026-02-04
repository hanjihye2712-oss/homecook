from django.urls import path
from . import views

app_name = 'homecook'

urlpatterns = [
    #index
    path('', views.HomecookLandingView.as_view(), name='landing'),
  
#   path("create/", views.HomecookCreateView.as_view(), name="homecook_create"),
#   path("update/", views.HomecookUpdateView.as_view(), name="homecook_update"),
#   path("delete/", views.HomecookDeleteView.as_view(), name="homecook_delte"),
   
    # My Challenge 페이지 (로그인 필수)
    path('my-challenge/', views.HomecookMyChallengeView.as_view(), name='my_challenge'),
    
    # Create Views (클래스명 변경에 맞춤)
    path('food-image/create/', views.HomecookFoodImageCreateView.as_view(), name='food_image_create'),
    path('receipt/create/', views.HomecookReceiptCreateView.as_view(), name='receipt_create'),
    path('recipe/create/', views.HomecookRecipeCreateView.as_view(), name='recipe_create'),
    path('journal/create/', views.HomecookJournalCreateView.as_view(), name='journal_create'),
]

