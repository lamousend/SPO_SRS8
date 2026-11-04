from contextvars import ContextVar

current_user = ContextVar('current_user', default=None)


class CurrentUserMiddleware:
    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        token = current_user.set(request.user)
        try:
            return self.get_response(request)
        finally:
            current_user.reset(token)
