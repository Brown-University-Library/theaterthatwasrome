import logging
import xml.etree.ElementTree as ET
from operator import itemgetter

import httpx2
from django.core.mail import mail_admins

from rome_app.lib import bdr_client
from rome_app.models import Annotation

logger = logging.getLogger('rome')


def fetch_url_content(url: str) -> httpx2.Response:
    """
    Fetches BDR metadata and raises an HTTP error when the request fails.
    Called by: views.page_detail(), views.print_detail(), views._get_book_pid_from_page_pid(), get_annotation_detail()
    """
    return bdr_client.request('GET', url)


def _get_annotation_name_info(mods_name: ET.Element) -> dict[str, str | None]:
    """
    Reads a contributor's name, role, and biography identifier.
    Called by: get_annotation_detail()
    """
    logger.debug(f'starting non-top-level-view _get_annotation_name_info() for mods_name, ``{mods_name}``')
    trp_id = Annotation.trp_id_from_name_node(mods_name)
    return {
        'name': mods_name[0].text,
        'role': mods_name[1][0].text.capitalize() if (mods_name[1][0].text) else 'Contributor',
        'trp_id': trp_id,
    }


def get_annotation_detail(annotation: dict[str, str]) -> dict:
    """
    Reads the annotation's XML metadata for display on a page or print.
    Called by: views.page_detail(), views.print_detail()
    """
    logger.debug('starting non-top-level-view get_annotation_detail() for annotation, ``{annotation}``')
    curr_annot = {}
    curr_annot['xml_uri'] = annotation['xml_uri']
    if 'edit_link' in annotation:
        curr_annot['edit_link'] = annotation['edit_link']
    curr_annot['has_elements'] = {
        'inscriptions': 0,
        'annotations': 0,
        'annotator': 0,
        'origin': 0,
        'title': 0,
        'abstract': 0,
        'genre': 0,
    }

    r = fetch_url_content(curr_annot['xml_uri'])
    root = ET.fromstring(r.content)
    for title in root.iter('{http://www.loc.gov/mods/v3}titleInfo'):
        if 'lang' in title.attrib and title.attrib['lang'] == 'en':
            curr_annot['title'] = title[0].text if title[0].text else ''
        else:
            curr_annot['orig_title'] = title[0].text if title[0].text else '[No Title]'
        curr_annot['has_elements']['title'] += 1

    curr_annot['names'] = []
    for name in root.iter('{http://www.loc.gov/mods/v3}name'):
        name_info = _get_annotation_name_info(name)
        if not name_info['trp_id']:
            mail_admins(
                subject='TTWR annotation error', message=f'{annotation["pid"]} annotation missing trp_id: {name_info}'
            )
        curr_annot['names'].append(name_info)
    curr_annot['names'] = sorted(curr_annot['names'], key=itemgetter('role', 'name'))
    for abstract in root.iter('{http://www.loc.gov/mods/v3}abstract'):
        curr_annot['abstract'] = abstract.text
        curr_annot['has_elements']['abstract'] = 1
    for genre in root.iter('{http://www.loc.gov/mods/v3}genre'):
        curr_annot['genre'] = genre.text
        curr_annot['has_elements']['genre'] = 1
    for origin in root.iter('{http://www.loc.gov/mods/v3}originInfo'):
        for impression in origin.iter('{http://www.loc.gov/mods/v3}dateOther'):
            curr_annot['impression'] = impression.text
            if impression.text is not None:
                curr_annot['has_elements']['impression'] = 1
        if len(origin) and origin[0].text:
            curr_annot['origin'] = origin[0].text
            curr_annot['has_elements']['origin'] = 1
    for impression in root.iter('{http://www.loc.gov/mods/v3}dateOther'):
        if impression.get('type') == 'impression' and len(impression):
            curr_annot['impression'] = impression[0].text
            curr_annot['has_elements']['impression'] = 1
    curr_annot['inscriptions'] = []
    curr_annot['annotations'] = []
    curr_annot['annotator'] = ''
    for note in root.iter('{http://www.loc.gov/mods/v3}note'):
        curr_note = {}
        for att in note.attrib:
            curr_note[att] = note.attrib[att]
        if note.text:
            curr_note['text'] = note.text
        if curr_note['type'].lower() == 'inscription' and note.text:
            curr_annot['inscriptions'].append(curr_note['displayLabel'] + ': ' + curr_note['text'])
            curr_annot['has_elements']['inscriptions'] = 1
        elif curr_note['type'].lower() == 'annotation' and note.text:
            curr_annot['annotations'].append(curr_note['displayLabel'] + ': ' + curr_note['text'])
            curr_annot['has_elements']['annotations'] = 1
        elif curr_note['type'].lower() == 'resp' and note.text:
            # display for the first annotator; ignore later annotators for now
            if not curr_annot['annotator']:
                curr_annot['annotator'] = note.text
                curr_annot['has_elements']['annotator'] = 1
    return curr_annot
