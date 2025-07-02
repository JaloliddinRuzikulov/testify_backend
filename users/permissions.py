from rest_framework import permissions


class IsAdmin(permissions.BasePermission):
    """Permission to allow only admin users"""
    
    def has_permission(self, request, view):
        return request.user.is_authenticated and request.user.is_admin


class IsExpert(permissions.BasePermission):
    """Permission to allow only expert users"""
    
    def has_permission(self, request, view):
        return request.user.is_authenticated and request.user.is_expert


class IsCreator(permissions.BasePermission):
    """Permission to allow only question creator users"""
    
    def has_permission(self, request, view):
        return request.user.is_authenticated and request.user.is_creator


class IsAdminOrExpert(permissions.BasePermission):
    """Permission to allow only admin or expert users"""
    
    def has_permission(self, request, view):
        return request.user.is_authenticated and (
            request.user.is_admin or request.user.is_expert)


class IsAdminOrSelf(permissions.BasePermission):
    """Permission to allow admins or the user themselves"""
    
    def has_object_permission(self, request, view, obj):
        return request.user.is_authenticated and (
            request.user.is_admin or obj == request.user)