from django.contrib import admin
from django.contrib.auth.admin import UserAdmin
from django.utils.translation import gettext_lazy as _
from .models import User
from .passport_models import PassportData, UserPassportLink, FaceAuthenticationLog


@admin.register(User)
class CustomUserAdmin(UserAdmin):
    """Admin configuration for custom user model"""

    fieldsets = (
        (None, {'fields': ('username', 'password')}),
        (_('Shaxsiy ma\'lumotlar'), {
            'fields': ('first_name', 'last_name', 'email', 'bio', 'profile_image')
        }),
        (_('Rol va mutaxassislik'), {
            'fields': ('role', 'expert_subject')
        }),
        (_('Passport ma\'lumotlari'), {
            'fields': ('pnfl', 'passport'),
            'classes': ('collapse',),
            'description': 'Foydalanuvchining passport ma\'lumotlari'
        }),
        (_('Biometrik ma\'lumotlar'), {
            'fields': ('face_descriptor',),
            'classes': ('collapse',),
            'description': 'Yuz tanish uchun base64 encoded descriptor'
        }),
        (_('Ruxsatlar'), {
            'fields': ('is_active', 'is_staff', 'is_superuser', 'groups', 'user_permissions'),
            'classes': ('collapse',)
        }),
        (_('Muhim sanalar'), {
            'fields': ('last_login', 'date_joined'),
            'classes': ('collapse',)
        }),
    )

    list_display = ('username', 'email', 'first_name', 'last_name', 'role', 'expert_subject', 'is_staff')
    list_filter = ('role', 'is_staff', 'is_superuser', 'is_active', 'expert_subject')


@admin.register(PassportData)
class PassportDataAdmin(admin.ModelAdmin):
    """Admin for PassportData model"""
    list_display = ('pinfl', 'passport_series', 'passport_number', 'first_name', 'last_name', 'birth_date')
    list_filter = ('issue_date', 'expire_date', 'created_at')
    search_fields = ('pinfl', 'passport_series', 'passport_number', 'first_name', 'last_name')
    readonly_fields = ('created_at', 'updated_at')
    
    fieldsets = (
        (_('Passport Information'), {
            'fields': ('passport_series', 'passport_number', 'pinfl')
        }),
        (_('Personal Information'), {
            'fields': ('first_name', 'last_name', 'middle_name', 'birth_date', 'address')
        }),
        (_('Document Details'), {
            'fields': ('issued_by', 'issue_date', 'expire_date')
        }),
        (_('Biometric Data'), {
            'fields': ('photo_base64', 'face_descriptors'),
            'classes': ('collapse',)
        }),
        (_('Timestamps'), {
            'fields': ('created_at', 'updated_at'),
            'classes': ('collapse',)
        }),
    )


@admin.register(UserPassportLink)
class UserPassportLinkAdmin(admin.ModelAdmin):
    """Admin for UserPassportLink model"""
    list_display = ('user', 'get_passport_info', 'verified', 'face_match_score', 'verified_at')
    list_filter = ('verified', 'created_at', 'verified_at')
    search_fields = ('user__username', 'passport_data__pinfl', 'passport_data__passport_number')
    readonly_fields = ('created_at', 'updated_at')
    
    def get_passport_info(self, obj):
        """Display passport information"""
        pd = obj.passport_data
        return f"{pd.passport_series}{pd.passport_number} - {pd.first_name} {pd.last_name}"
    get_passport_info.short_description = _('Passport')
    
    fieldsets = (
        (_('Link Information'), {
            'fields': ('user', 'passport_data')
        }),
        (_('Verification'), {
            'fields': ('verified', 'verified_at', 'face_match_score')
        }),
        (_('Timestamps'), {
            'fields': ('created_at', 'updated_at'),
            'classes': ('collapse',)
        }),
    )


@admin.register(FaceAuthenticationLog)
class FaceAuthenticationLogAdmin(admin.ModelAdmin):
    """Admin for FaceAuthenticationLog model"""
    list_display = ('user', 'status', 'match_score', 'ip_address', 'attempted_at')
    list_filter = ('status', 'attempted_at')
    search_fields = ('user__username', 'ip_address')
    readonly_fields = ('user', 'status', 'match_score', 'ip_address', 'user_agent', 'error_message', 'attempted_at')
    
    def has_add_permission(self, request):
        """Prevent adding logs manually"""
        return False
    
    def has_change_permission(self, request, obj=None):
        """Make logs read-only"""
        return False
    
    def has_delete_permission(self, request, obj=None):
        """Allow deletion for cleanup"""
        return request.user.is_superuser