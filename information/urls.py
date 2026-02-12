from django.urls import path
from . import views

app_name = 'information'

urlpatterns = [
    # 통합 대시보드 (메인)
    path('', views.IntegratedDashboardView.as_view(), name='integrated_dashboard'),

    # 목록
    path('list/', views.TransactionListView.as_view(), name='transaction_list'),

    # 상세
    path('<int:pk>/', views.TransactionDetailView.as_view(), name='transaction_detail'),

    # 생성
    path('create/', views.TransactionCreateView.as_view(), name='transaction_create'),

    # 수정
    path('<int:pk>/update/', views.TransactionUpdateView.as_view(), name='transaction_update'),

    # 삭제
    path('<int:pk>/delete/', views.TransactionDeleteView.as_view(), name='transaction_delete'),

    # 포인트
    path('points/', views.points_view, name='points'),
    path('transfer-to-seoulpay/', views.transfer_to_seoulpay, name='transfer_to_seoulpay'),

    # ============= 계좌 =============
    # 목록
    path('accounts/', views.AccountListView.as_view(), name='account_list'),

    # 생성
    path('accounts/create/', views.AccountCreateView.as_view(), name='account_create'),

    # 상세
    path('accounts/<int:pk>/', views.AccountDetailView.as_view(), name='account_detail'),

    # 수정
    path('accounts/<int:pk>/update/', views.AccountUpdateView.as_view(), name='account_update'),

    # 삭제
    path('accounts/<int:pk>/delete/', views.AccountDeleteView.as_view(), name='account_delete'),
]
