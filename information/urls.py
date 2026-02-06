from django.urls import path
from . import views

app_name = 'information'

urlpatterns = [
    # 목록
    path('', views.TransactionListView.as_view(), name='transaction_list'),
    
    # 상세
    path('<int:pk>/', views.TransactionDetailView.as_view(), name='transaction_detail'),
    
    # 생성
    path('create/', views.TransactionCreateView.as_view(), name='transaction_create'),
    
    # 수정
    path('<int:pk>/update/', views.TransactionUpdateView.as_view(), name='transaction_update'),
    
    # 삭제
    path('<int:pk>/delete/', views.TransactionDeleteView.as_view(), name='transaction_delete'),
]
