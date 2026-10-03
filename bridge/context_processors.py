from django.conf import settings
from .access import coordinator

def navigation(request):
    profile = getattr(request.user, 'profile', None) if request.user.is_authenticated else None
    return {
        'is_coordinator': coordinator(request.user),
        'current_school': profile.school if profile else None,
        'role_label': 'Quản trị viên' if request.user.is_superuser else (profile.get_role_display() if profile else 'Chưa được phân quyền'),
        'support_email': settings.SUPPORT_EMAIL,
    }
