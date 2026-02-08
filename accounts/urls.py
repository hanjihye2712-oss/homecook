from django.urls import path
from . import views
from django.contrib.auth import views as auth_views

app_name = 'accounts'

urlpatterns = [
    path("signup/", views.signup, name="signup"),
    # Django 기본 제공 LoginView 사용
    path("login/", auth_views.LoginView.as_view(template_name='registration/login.html'), name="login"),
    path("logout/", views.custom_logout, name="custom_logout"), 
]