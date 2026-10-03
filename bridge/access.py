from django.core.exceptions import PermissionDenied
from .models import Profile

def coordinator(user):
    return user.is_authenticated and (user.is_superuser or (hasattr(user, 'profile') and user.profile.role == Profile.Role.COORDINATOR))

def school_id(user):
    if not user.is_authenticated or not hasattr(user, 'profile'):
        return None
    return user.profile.school_id

def require_school(user, target_id):
    if not coordinator(user) and school_id(user) != target_id:
        raise PermissionDenied

def require_coordinator(user):
    if not coordinator(user):
        raise PermissionDenied

def accessible_loans(user, qs):
    from django.db.models import Q
    if coordinator(user):
        return qs
    sid = school_id(user)
    if sid is None:
        return qs.none()
    return qs.filter(Q(inventory__school_id=sid) | Q(need__school_id=sid))
