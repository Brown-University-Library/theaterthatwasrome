import logging

from django.http import HttpRequest, HttpResponse
from django.shortcuts import render
from django.utils.cache import add_never_cache_headers


def render_content(request: HttpRequest, template: str, context: dict) -> HttpResponse:
    """
    Renders local content without caching an incomplete page during a BDR outage.
    Called by: views.essay_list(), views.essay_detail(), views.shop_detail(), views.biography_detail()
    """
    response = render(request, template, context)
    if context.get('bdr_unavailable'):
        add_never_cache_headers(response)
    return response


def unavailable_response(request: HttpRequest) -> HttpResponse:
    """
    Renders an outage notice without looking up BDR content.
    Called by: BdrFailureMiddleware.process_exception()
    """
    response = render(
        request,
        'rome_templates/bdr_unavailable.html',
        {
            'title': 'Content temporarily unavailable',
            'common_style': 'rome/css/common.css',
            'usr_style': 'rome/css/content.css',
            'brown_image': 'rome/images/brown-logo.gif',
            'stg_image': 'rome/images/stg-logo.gif',
            'write_failed': request.method not in {'GET', 'HEAD'},
        },
        status=503,
    )
    response['Retry-After'] = '60'
    add_never_cache_headers(response)
    ## Only mark the request after the outage template renders successfully.
    request.META['rome.bdr_unavailable_response'] = True
    return response


class SkipHandledBdrFailure(logging.Filter):
    def filter(self, record: logging.LogRecord) -> bool:
        """
        Excludes only deliberately handled BDR outage responses from administrator email.
        Called by: logging.Handler.filter()
        """
        request = getattr(record, 'request', None)
        handled = (
            record.name == 'django.request'
            and getattr(record, 'status_code', None) == 503
            and isinstance(request, HttpRequest)
            and request.META.get('rome.bdr_unavailable_response') is True
            and not record.exc_info
        )
        return not handled
