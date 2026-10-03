import math
import unicodedata

from axes.handlers.database import AxesDatabaseHandler
from axes.models import AccessAttempt
from django.conf import settings
from django.shortcuts import render
from django.utils import timezone


def no_client_ip(request):
    # Limits follow the account across networks, without trusting proxy headers.
    return None


def login_username(request, credentials=None):
    value = (credentials or {}).get('username')
    if value is None:
        value = request.POST.get('username', '')
    # Match Django's UsernameField normalization, including surrounding spaces.
    return unicodedata.normalize('NFKC', str(value).strip())


class AccountLoginHandler(AxesDatabaseHandler):
    def user_login_failed(self, sender, credentials, request=None, **kwargs):
        if request is not None:
            # Axes normally creates rows per browser. One row per username keeps
            # the full cooldown intact even when an attacker changes browsers.
            request.axes_user_agent = ''
        return super().user_login_failed(sender, credentials, request, **kwargs)


def login_locked_out(request, original_response=None, credentials=None):
    last_attempt = AccessAttempt.objects.filter(
        username=login_username(request, credentials),
    ).order_by('-attempt_time').values_list('attempt_time', flat=True).first()
    retry_at = (last_attempt or timezone.now()) + settings.AXES_COOLOFF_TIME
    retry_after = max(1, math.ceil((retry_at - timezone.now()).total_seconds()))
    response = render(request, 'registration/locked_out.html', {
        'retry_at': retry_at,
        'retry_minutes': math.ceil(retry_after / 60),
        'failure_limit': settings.AXES_FAILURE_LIMIT,
        'login_url': '/admin/login/' if request.path.startswith('/admin/') else settings.LOGIN_URL,
    }, status=429)
    response['Retry-After'] = str(retry_after)
    response['Cache-Control'] = 'no-store'
    return response
