from django.conf import settings
from django.http import HttpResponse

from .view_utils import is_rate_limited


class AuthThrottleMiddleware:
    """Cover the standard admin login and every password-reset POST route."""
    def __init__(self, get_response):
        self.get_response = get_response

    def process_view(self, request, view_func, view_args, view_kwargs):
        match = request.resolver_match
        if request.method != 'POST' or match is None:
            return None
        if match.view_name == 'admin:login' or (
            match.namespace == 'core' and match.url_name.startswith('password_reset')
        ):
            if is_rate_limited(request, 'auth_sensitive', settings.AUTH_POST_LIMIT, settings.AUTH_WINDOW_SECONDS):
                response = HttpResponse('Слишком много попыток. Повторите позже.', status=429)
                response['Retry-After'] = str(settings.AUTH_WINDOW_SECONDS)
                return response

    def __call__(self, request):
        return self.get_response(request)
