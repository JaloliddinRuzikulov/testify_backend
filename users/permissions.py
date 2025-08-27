from rest_framework import permissions


class IsSuperAdmin(permissions.BasePermission):
    """Permission to allow only super admin users"""
    
    def has_permission(self, request, view):
        return request.user.is_authenticated and request.user.is_superadmin


class IsAdmin(permissions.BasePermission):
    """Permission to allow only admin users (includes SuperAdmin)"""
    
    def has_permission(self, request, view):
        return request.user.is_authenticated and request.user.is_admin


class IsQBExpert(permissions.BasePermission):
    """Permission to allow only Question Bank expert users"""
    
    def has_permission(self, request, view):
        return request.user.is_authenticated and request.user.is_qb_expert


class IsQExpert(permissions.BasePermission):
    """Permission to allow only Question expert users"""
    
    def has_permission(self, request, view):
        return request.user.is_authenticated and request.user.is_q_expert


class IsExpert(permissions.BasePermission):
    """Permission to allow only expert users (QB Expert or Q Expert)"""
    
    def has_permission(self, request, view):
        return request.user.is_authenticated and request.user.is_expert


class IsCreator(permissions.BasePermission):
    """Permission to allow only Q creator users"""
    
    def has_permission(self, request, view):
        return request.user.is_authenticated and request.user.is_creator


class IsAdminOrExpert(permissions.BasePermission):
    """Permission to allow only admin or expert users"""
    
    def has_permission(self, request, view):
        return request.user.is_authenticated and (
            request.user.is_admin or request.user.is_expert)


class CanManageQuestions(permissions.BasePermission):
    """Permission for users who can manage questions"""
    
    def has_permission(self, request, view):
        return request.user.is_authenticated and request.user.can_manage_questions


class CanManageBanks(permissions.BasePermission):
    """Permission for users who can manage question banks"""
    
    def has_permission(self, request, view):
        return request.user.is_authenticated and request.user.can_manage_banks


class CanManageUsers(permissions.BasePermission):
    """Permission for users who can manage other users"""
    
    def has_permission(self, request, view):
        return request.user.is_authenticated and request.user.can_manage_users


class IsAdminOrSelf(permissions.BasePermission):
    """Permission to allow admins or the user themselves"""
    
    def has_object_permission(self, request, view, obj):
        return request.user.is_authenticated and (
            request.user.is_admin or obj == request.user)