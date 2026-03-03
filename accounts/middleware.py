from django.shortcuts import redirect

EXEMPT_PATHS = ['/login/', '/register/', '/verify-otp/', '/logout/',
                '/api/', '/static/', '/media/', '/onboarding/']

class OnboardingMiddleware:
    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        if (request.user.is_authenticated
                and not request.user.is_staff
                and not request.user.has_seen_onboarding
                and not any(request.path.startswith(p) for p in EXEMPT_PATHS)):
            return redirect('/onboarding/')
        return self.get_response(request)