from django.contrib import admin
from django.contrib.auth.admin import UserAdmin
from .models import CustomUser, HelpRequest, VolunteerTask, VolunteerApplication, ContentPage, NewsPost

@admin.register(CustomUser)
class CustomUserAdmin(UserAdmin):
    fieldsets = UserAdmin.fieldsets + (
        ('Additional Info', {'fields': ('role', 'phone_number', 'middle_name', 'city', 'avatar_url', 'total_hours', 'rank_title')}),
    )
    list_display = ('username', 'phone_number', 'email', 'get_full_name_repr', 'role', 'city', 'total_hours')
    list_filter = ('role', 'city')
    search_fields = ('username', 'phone_number', 'email', 'first_name', 'last_name', 'middle_name')

    def get_full_name_repr(self, obj):
        return obj.get_full_name()
    get_full_name_repr.short_description = 'Full Name'

@admin.register(HelpRequest)
class HelpRequestAdmin(admin.ModelAdmin):
    list_display = ('id', 'client', 'category', 'status', 'created_at')
    list_filter = ('status', 'category')
    search_fields = ('client__username', 'description', 'address')

@admin.register(VolunteerTask)
class VolunteerTaskAdmin(admin.ModelAdmin):
    list_display = ('title', 'date', 'time', 'duration', 'status', 'assigned_volunteer')
    list_filter = ('status', 'date')
    search_fields = ('title', 'assigned_volunteer__username')

@admin.register(VolunteerApplication)
class VolunteerApplicationAdmin(admin.ModelAdmin):
    list_display = ('id', 'user', 'status', 'has_personal_car', 'submitted_at')
    list_filter = ('status', 'has_personal_car')
    search_fields = ('user__username', 'skills')

@admin.register(ContentPage)
class ContentPageAdmin(admin.ModelAdmin):
    list_display = ('slug', 'is_published', 'updated_at')
    list_filter = ('is_published',)
    search_fields = ('slug', 'title_kk', 'title_ru')

@admin.register(NewsPost)
class NewsPostAdmin(admin.ModelAdmin):
    list_display = ('title_kk', 'is_published', 'published_at')
    list_filter = ('is_published',)
    search_fields = ('title_kk', 'title_ru', 'body_kk', 'body_ru')
