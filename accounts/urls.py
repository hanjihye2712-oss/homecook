from django.urls import path
from . import views

urlpatterns = [
    path("signup/", views.signup, name="signup"),
    path("logout/", views.custom_logout, name="custom_logout"), 
]