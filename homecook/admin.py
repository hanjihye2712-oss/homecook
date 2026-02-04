# homecook/admin.py
from django.contrib import admin
from .models import FoodImage, Receipt, Recipe, Journal

@admin.register(FoodImage)
class FoodImageAdmin(admin.ModelAdmin):
    list_display = ['id', 'user', 'title', 'created_at']
    list_filter = ['created_at']
    search_fields = ['title', 'user__username']

@admin.register(Receipt)
class ReceiptAdmin(admin.ModelAdmin):
    list_display = ['id', 'user', 'is_processed', 'created_at']
    list_filter = ['is_processed', 'created_at']

@admin.register(Recipe)
class RecipeAdmin(admin.ModelAdmin):
    list_display = ['id', 'title', 'user', 'views', 'created_at']
    list_filter = ['created_at']
    search_fields = ['title', 'content']

@admin.register(Journal)
class JournalAdmin(admin.ModelAdmin):
    list_display = ['id', 'title', 'user', 'visibility', 'created_at']
    list_filter = ['visibility', 'created_at']
    search_fields = ['title', 'content']