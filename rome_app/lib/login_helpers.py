from urllib.parse import urlsplit

from django.urls import Resolver404, get_script_prefix, resolve
from django.utils.http import url_has_allowed_host_and_scheme


def editing_destination(next_url: str | None) -> str:
    """
    Validates a return link to one of the website's editing pages.
    Called by: views.login_page()
    """
    destination = ''
    if next_url and url_has_allowed_host_and_scheme(next_url, allowed_hosts=set()):
        next_url = next_url.strip()
        path = urlsplit(next_url).path
        prefix = get_script_prefix()
        if path.startswith(prefix):
            path = path[len(prefix) - 1 :]
            try:
                match = resolve(path)
            except Resolver404:
                match = None
            if match is not None and match.url_name in {
                'new_annotation',
                'edit_annotation',
                'new_print_annotation',
                'edit_print_annotation',
                'new_genre',
                'new_role',
                'new_biography',
            }:
                destination = next_url
    return destination
