from django.shortcuts import render, redirect
from django.contrib.auth import logout
from django.http import HttpResponseRedirect
from django.urls import reverse
from .forms import CustomUserCreationForm

def signup(request):
    if request.method == "POST":
        form = CustomUserCreationForm(request.POST)
        if form.is_valid():
            form.save()
            return HttpResponseRedirect(reverse("login"))
    else:
        form = CustomUserCreationForm()
    return render(request, "accounts/signup.html", {"form": form})

def custom_logout(request):
    logout(request)
    return redirect('homecook:main_index')
