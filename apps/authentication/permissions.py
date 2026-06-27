"""
Permissions personnalisées GnExpress
Chaque rôle a des droits précis sur les ressources.
"""
from rest_framework.permissions import BasePermission


class IsAdmin(BasePermission):
    """Administrateur - accès total"""
    def has_permission(self, request, view):
        return bool(request.user and request.user.is_authenticated and request.user.is_admin)


class IsClient(BasePermission):
    def has_permission(self, request, view):
        return bool(request.user and request.user.is_authenticated and
                    request.user.role == 'CLIENT')


class IsLivreur(BasePermission):
    def has_permission(self, request, view):
        return bool(request.user and request.user.is_authenticated and
                    request.user.role == 'LIVREUR')


class IsRestaurant(BasePermission):
    def has_permission(self, request, view):
        return bool(request.user and request.user.is_authenticated and
                    request.user.role == 'RESTAURANT')


class IsBoutiquierr(BasePermission):
    def has_permission(self, request, view):
        return bool(request.user and request.user.is_authenticated and
                    request.user.role == 'BOUTIQUIERR')


class IsCoursier(BasePermission):
    def has_permission(self, request, view):
        return bool(request.user and request.user.is_authenticated and
                    request.user.role == 'COURSIER')


class IsAdminOrReadOnly(BasePermission):
    """Admin peut tout faire, les autres peuvent lire"""
    def has_permission(self, request, view):
        if request.method in ('GET', 'HEAD', 'OPTIONS'):
            return bool(request.user and request.user.is_authenticated)
        return bool(request.user and request.user.is_authenticated and request.user.is_admin)


class IsOwnerOrAdmin(BasePermission):
    """Propriétaire de l'objet ou admin"""
    def has_object_permission(self, request, view, obj):
        if request.user.is_admin:
            return True
        owner = getattr(obj, 'owner', None) or getattr(obj, 'user', None) or getattr(obj, 'client', None)
        return owner == request.user


class IsLivreurOrAdmin(BasePermission):
    def has_permission(self, request, view):
        return bool(request.user and request.user.is_authenticated and
                    (request.user.role == 'LIVREUR' or request.user.is_admin))


class IsCoursierOrAdmin(BasePermission):
    def has_permission(self, request, view):
        return bool(request.user and request.user.is_authenticated and
                    (request.user.role == 'COURSIER' or request.user.is_admin))


class IsRestaurantOrAdmin(BasePermission):
    def has_permission(self, request, view):
        return bool(request.user and request.user.is_authenticated and
                    (request.user.role == 'RESTAURANT' or request.user.is_admin))


class IsBoutiquierrOrAdmin(BasePermission):
    def has_permission(self, request, view):
        return bool(request.user and request.user.is_authenticated and
                    (request.user.role == 'BOUTIQUIERR' or request.user.is_admin))
