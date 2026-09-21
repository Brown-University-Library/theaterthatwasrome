from rome_app.lib.bdr_client import BdrUnavailable
from rome_app.models import Biography, Essay, Shop, annotations_by_books_and_prints


def related_works(item: Essay | Shop, context: dict) -> list[dict]:
    """
    Omits unavailable related works and skips further BDR lookups for this page.
    Called by: views.essay_list(), views.essay_detail(), views.shop_detail()
    """
    works = []
    if not context.get('bdr_unavailable'):
        try:
            works = list(item.related_works())
        except BdrUnavailable:
            context['bdr_unavailable'] = True
    return works


def biography_related_content(bio: Biography) -> dict:
    """
    Gathers related BDR content while preserving the biography during an outage.
    Called by: views.biography_detail()
    """
    context: dict = {'books': [], 'prints': [], 'pages_books': {}}
    try:
        context['books'] = bio.books()
        prints_search = bio.prints()
        pages_books, prints_mentioned = annotations_by_books_and_prints(bio.name)
        context['pages_books'] = pages_books
        context['prints'] = [item for item in prints_mentioned if item not in prints_search] + prints_search
    except BdrUnavailable:
        context['bdr_unavailable'] = True
    return context
