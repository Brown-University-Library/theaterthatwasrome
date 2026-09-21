from django.http import HttpRequest, HttpResponse
from django.utils.deprecation import MiddlewareMixin

from rome_app.lib.bdr_client import BdrUnavailable
from rome_app.lib.bdr_failure import unavailable_response


class BdrFailureMiddleware(MiddlewareMixin):
    def process_exception(self, request: HttpRequest, exception: Exception) -> HttpResponse | None:
        """
        Handles temporary BDR failures while leaving other exceptions to Django.
        Called by: django.core.handlers.base.BaseHandler.process_exception_by_middleware()
        """
        response = None
        if isinstance(exception, BdrUnavailable):
            response = unavailable_response(request)
        return response
