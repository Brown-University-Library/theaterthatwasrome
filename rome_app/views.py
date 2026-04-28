import datetime
import json
import logging
import pprint
import re
import requests
import xml.etree.ElementTree as ET
from operator import itemgetter, methodcaller

import trio

from django.conf import settings
from django.http import HttpResponse, HttpResponseNotFound, HttpResponseServerError, HttpResponseRedirect
from django.forms.formsets import formset_factory
from django.core.exceptions import ObjectDoesNotExist
from django.core.mail import mail_admins
from django.core.paginator import Paginator
from django.urls import reverse, reverse_lazy
from django.shortcuts import render
from django.template.response import SimpleTemplateResponse
from django.utils.html import escape, escapejs
from django.contrib.auth.decorators import login_required

from .models import (
        InvalidNameError,
        Biography,
        Document,
        Essay,
        Static,
        Book,
        Annotation,
        Page,
        annotations_by_books_and_prints,
        Print,
        Shop,
        get_full_title_static,
        zoom_viewer_url,
        annotation_xml_url,
    )
from .app_settings import BDR_SERVER, BOOKS_PER_PAGE, PID_PREFIX, logger

from rome_app.lib import version_helper
from rome_app.lib.version_helper import GatherCommitAndBranchData


def temp_roles_checker(request):
    """ Checks biography-roles against Roles table.
        Called by `__main__`. """
    log.debug( '\n\nstarting temp_roles_checker()' )
    from rome_app.lib import roles_checker
    problems = roles_checker.run_code()
    data = {
        '__meta__': { 'bios_with_issues_count': len(problems), 'timestamp': str(datetime.datetime.now()) }, 
        'data': problems
        }
    jsn = json.dumps( data, sort_keys=False, indent=2 )
    return HttpResponse( jsn, content_type='application/json; charset=utf-8' )


def annotation_order(s): 
    retval = re.sub("[^0-9]", "", first_word(s['orig_title'] if 'orig_title' in s else s['title']))
    return int(retval) if retval != '' else 0
    

def first_word(s): return s.split(" ")[0] if s else ""


def std_context(path, style="rome/css/content.css",title="The Theater that was Rome"):
    pathparts = path.split(u'/')
    url = reverse('index')
    breadcrumbs = [{'url': url, 'name': 'The Theater that was Rome'}]

    for node in pathparts:
        if node:
            if node == 'rome' or node == 'projects':
                continue
            url += node + u'/'
            breadcrumb_name = ' '.join(part for part in node.split('_') if part).title() or node.title()
            obj = {'url': url, 'name': breadcrumb_name}
            breadcrumbs.append(obj)

    context={}
    context['common_style']="rome/css/common.css"
    context['usr_style']=style
    context['title']=title
    context['cpydate']=2017
    context['home_image']="rome/images/home.gif"
    context['brown_image']="rome/images/brown-logo.gif"
    context['stg_image']="rome/images/stg-logo.gif"
    context['page_documentation']=""
    context['breadcrumbs']=breadcrumbs
    return context


def index(request):
    logger.debug( '\n\nstarting index()' )
    context=std_context(request.path, style="rome/css/home.css")
    return render(request, 'rome_templates/index.html', context)

def about(request):
    logger.debug( '\n\nstarting about()' )
    context = std_context(request.path, style="rome/css/links.css")
    try:
        about = Static.objects.get(title="About")
    except ObjectDoesNotExist:
        return HttpResponseNotFound('Static About Not Found')
    context['about_text'] = about.text
    context['about_title'] = about.title
    return render(request, 'rome_templates/about.html', context)



def book_list(request):
    logger.debug( '\n\nstarting book_list()' )
    context = std_context(request.path, )
    collection = request.GET.get('filter', 'both')
    sort_by = request.GET.get('sort_by', 'title')

    buonanno = ""
    if(collection == 'buonanno'):
        buonanno = "+AND+(note:buonanno)"
    elif(collection == 'library'):
        buonanno = "+NOT+(note:buonanno)"
    try:
        book_list = Book.search(query="genre_aat:book*"+buonanno)
    except Exception as e:
        # logger.error(f'book_list view error getting book_list data: {e}')
        logger.exception(f'book_list view error getting book_list data: {e}')
        return HttpResponse('error loading list of books', status=500)
    sort_by = Book.SORT_OPTIONS.get(sort_by, 'title_sort')
    book_list=sorted(book_list,key=methodcaller('sort_key', sort_by))

    page = request.GET.get('page', 1)
    PAGIN=Paginator(book_list, BOOKS_PER_PAGE);

    page_list = []
    for i in PAGIN.page_range:
        page_list.append(PAGIN.page(i).object_list)

    context['num_pages']=PAGIN.num_pages
    context['page_range']=PAGIN.page_range
    context['PAGIN']=PAGIN

    context['sorting'] = sort_by
    context['sort_options'] = Book.SORT_OPTIONS
    context['page_list'] = page_list

    context['curr_page'] = page
    context['num_results'] = len(book_list)
    context['results_per_page'] = BOOKS_PER_PAGE

    context['filter_options'] = [("Buonanno", "buonanno"), ("All", "both"), ("Library", "library")]
    context['filter']=collection
    # logger.debug( f'context, ``{pprint.pformat(context)}``' )
    return render(request, 'rome_templates/book_list.html', context)


def book_detail(request, book_id):
    logger.debug( '\n\nstarting book_detail()' )
    book_list_page = request.GET.get('book_list_page', 1)
    book_list_sort_by = request.GET.get('book_list_sort_by', 'title')
    context = std_context(request.path)
    #Back to list HREF
    context['back_to_book_href'] = u'%ssort_by=%s?page=%s?' % (reverse('books'), book_list_sort_by, book_list_page)
    book = Book.get_or_404(pid="%s:%s" % (PID_PREFIX, book_id))
    context['book'] = book
    context['essays'] = book.essays()

    context['breadcrumbs'][-1]['name'] = breadcrumb_detail(context)
    grp = 20 # group size for lookups
    pages = context['book'].pages()
    pid_groups = [["%s:%s" % (PID_PREFIX, x.id) for x in pages[i:i+grp]] for i in range(0, len(pages), grp)]
    url = "https://%s/api/search?q=%s+AND+display:BDR_PUBLIC&fl=rel_is_annotation_of_ssim&rows=6000&callback=mark_annotated"
    annot_lookups = [url % (BDR_SERVER, "rel_is_annotation_of_ssim:(\"" + ("\"+OR+\"".join(l)) + "\")") for l in pid_groups]
    context['annot_lookups'] = annot_lookups
    return render(request, 'rome_templates/book_detail.html', context)


def _fetch_url_content(url):
    logger.debug( f'starting non-top-level-view _fetch_url_content with url, ``{url}``' )
    r = requests.get(url, timeout=60)
    if r.ok:
        return r
    else:
        logger.error(f'error retrieving {url}: {r.status_code} - {r.text}')
        raise Exception(f'{r.status_code}')


def page_detail(request, page_id: str, book_id=None):  # book_id will be type str or None
    logger.debug( '\n\nstarting page_detail()' )
    # logger.debug( f'type(page_id), ``{type(page_id)}``; page_id, ``{page_id}``' )
    # logger.debug( f'type(book_id), ``{type(book_id)}``; book_id, ``{book_id}``' )
    assert type( page_id ) == str
    assert type( book_id ) in [ str, type(None )]
    page_pid = '%s:%s' % (PID_PREFIX, page_id)
    this_page = Page.get_or_404(page_pid)
    context = std_context(request.path, )
    if book_id:
        book_pid = '%s:%s' % (PID_PREFIX, book_id)
    else:
        book_pid: str = _get_book_pid_from_page_pid(u'%s' % page_pid)
        book_id = book_pid.split(':')[-1]
    if not book_id:
        return HttpResponseNotFound('Book for this page not found.')
    
    context['user'] = request.user
    if request.user.is_authenticated:
        context['create_annotation_link'] = reverse('new_annotation', kwargs={'book_id':book_id, 'page_id':page_id})

    book_list_page = request.GET.get('book_list_page', None)

    context['book_mode'] = 1
    context['print_mode'] = 0
    if book_list_page:
        context['back_to_book_href'] = u'%s?page=%s' % (reverse('books'), book_list_page)
        context['back_to_thumbnail_href'] = u'%s?book_list_page=%s' % (reverse('thumbnail_viewer', kwargs={'book_id':book_id}), book_list_page)
    else:
        context['back_to_book_href'] = reverse('books')
        context['back_to_thumbnail_href'] = reverse('thumbnail_viewer', kwargs={'book_id':book_id})

    context['studio_url'] = this_page.studio_uri
    context['book_id'] = book_id

    book_json_uri = 'https://%s/api/items/%s/' % (BDR_SERVER, book_pid)
    try:
        r = _fetch_url_content(book_json_uri)
    except Exception:
        return HttpResponseServerError('Error retrieving content.')
    book_json = json.loads(r.text)
    context['short_title'] = book_json['brief']['title']
    context['title'] = get_full_title_static(book_json)
    try:
        author_list = book_json['contributor_display']
        authors = ""
        for i in range(len(author_list)):
            if i == len(author_list)-1:
                authors += author_list[i]
            else:
                authors += author_list[i]+"; "
        context['authors'] = authors
    except Exception:
        context['authors'] = "contributor(s) not available"
    try:
        context['date'] = book_json['dateIssued'][0:4]
    except Exception:
        try:
            context['date'] = book_json['dateCreated'][0:4]
        except Exception:
            context['date'] = "n.d."
    context['note'] = "no note"
    try:
        if 'Buonanno' in book_json['note'][0]:
            context['note'] = "From the personal collection of Vincent J. Buonanno"
    except (KeyError, TypeError):
        pass
    context['det_img_view_src'] = this_page.embedded_viewer_src()

    context['breadcrumbs'][-2]['name'] = breadcrumb_detail(context, view="print")

    # annotations/metadata
    annotations = this_page.relations['hasAnnotation']
    context['has_annotations'] = len(annotations)
    context['annotation_uris'] = []
    context['annotations'] = []
    for annotation in annotations:
        anno_id = annotation['pid'].split(':')[-1]
        if request.user.is_authenticated:
            link = reverse('edit_annotation', kwargs={'book_id': book_id, 'page_id': page_id, 'anno_id': anno_id})
            annotation['edit_link'] = link
        annot_xml_uri = annotation_xml_url(annotation['pid'])
        context['annotation_uris'].append(annot_xml_uri)
        annotation['xml_uri'] = annot_xml_uri
        curr_annot = get_annotation_detail(annotation)
        context['annotations'].append(curr_annot)
    if(context['annotations']):
        context['annotations'] = sorted(context['annotations'], key=lambda annote: annotation_order(annote))

    prev_id, next_id = _get_prev_next_ids(book_json, page_pid)
    context['prev_pid'] = prev_id
    context['next_pid'] = next_id
    context['essays'] = this_page.essays()

    context['breadcrumbs'][-1]['name'] = "Image " + this_page.rel_has_pagination_ssim[0]
    return render(request, 'rome_templates/page_detail.html', context)


def _get_annotation_name_info(mods_name):
    logger.debug( f'starting non-top-level-view _get_annotation_name_info() for mods_name, ``{mods_name}``' )
    trp_id = Annotation.trp_id_from_name_node(mods_name)
    return {
        'name': mods_name[0].text,
        'role': mods_name[1][0].text.capitalize() if(mods_name[1][0].text) else "Contributor",
        'trp_id': trp_id,
    }

def get_annotation_detail(annotation):
    logger.debug( 'starting non-top-level-view get_annotation_detail() for annotation, ``{annotation}``' )
    curr_annot={}
    curr_annot['xml_uri'] = annotation['xml_uri']
    if 'edit_link' in annotation:
        curr_annot['edit_link'] = annotation['edit_link']
    curr_annot['has_elements'] = {'inscriptions':0, 'annotations':0, 'annotator':0, 'origin':0, 'title':0, 'abstract':0, 'genre':0}

    r = _fetch_url_content(curr_annot['xml_uri'])
    root = ET.fromstring(r.content)
    for title in root.iter('{http://www.loc.gov/mods/v3}titleInfo'):
        if 'lang' in title.attrib and title.attrib['lang'] == 'en':
            curr_annot['title'] = title[0].text if title[0].text else ""
        else:
            curr_annot['orig_title'] = title[0].text if title[0].text else "[No Title]"
        curr_annot['has_elements']['title'] += 1

    curr_annot['names'] = []
    for name in root.iter('{http://www.loc.gov/mods/v3}name'):
        name_info = _get_annotation_name_info(name)
        if not name_info['trp_id']:
            mail_admins(subject='TTWR annotation error',
                    message=f'{annotation["pid"]} annotation missing trp_id: {name_info}')
        curr_annot['names'].append(name_info)
    curr_annot['names'] = sorted(curr_annot['names'], key=itemgetter("role", "name"))
    for abstract in root.iter('{http://www.loc.gov/mods/v3}abstract'):
        curr_annot['abstract']=abstract.text
        curr_annot['has_elements']['abstract']=1
    for genre in root.iter('{http://www.loc.gov/mods/v3}genre'):
        curr_annot['genre'] = genre.text
        curr_annot['has_elements']['genre']=1
    for origin in root.iter('{http://www.loc.gov/mods/v3}originInfo'):
        try:
            for impression in origin.iter('{http://www.loc.gov/mods/v3}dateOther'):
                try:
                    curr_annot['impression']=impression.text
                    if impression.text != None:
                        curr_annot['has_elements']['impression']=1
                except Exception:
                    pass
            curr_annot['origin']=origin[0].date
            curr_annot['has_elements']['origin']=1
        except Exception:
            pass
    for impression in root.iter('{http://www.loc.gov/mods/v3}dateOther'):
        try:
            if impression.attrib['type'] == "impression":
                curr_annot['impression']=impression[0].text
                curr_annot['has_elements']['impression']=1
        except Exception:
            pass
    curr_annot['inscriptions'] = []
    curr_annot['annotations'] = []
    curr_annot['annotator'] = ""
    for note in root.iter('{http://www.loc.gov/mods/v3}note'):
        curr_note={}
        for att in note.attrib:
            curr_note[att]=note.attrib[att]
        if note.text:
            curr_note['text']=note.text
        if curr_note['type'].lower()=='inscription' and note.text:
            curr_annot['inscriptions'].append(curr_note['displayLabel']+": "+curr_note['text'])
            curr_annot['has_elements']['inscriptions']=1
        elif curr_note['type'].lower()=='annotation' and note.text:
            curr_annot['annotations'].append(curr_note['displayLabel']+": "+curr_note['text'])
            curr_annot['has_elements']['annotations']=1
        elif curr_note['type'].lower()=='resp' and note.text:
            #display for the first annotator; ignore later annotators for now
            if not curr_annot['annotator']:
                curr_annot['annotator'] = note.text
                curr_annot['has_elements']['annotator'] = 1
    return curr_annot


def print_list(request):
    logger.debug( '\n\nstarting print_list()' )
    page = request.GET.get('page', 1)
    sort_by = request.GET.get('sort_by', 'title')
    if sort_by not in ['title', 'authors', 'date']:
        sort_by = 'title'
    collection = request.GET.get('filter', 'both')
    context = std_context(request.path, title="The Theater that was Rome - Prints")
    context['page_documentation'] = 'Browse the prints in the Theater that was Rome collection. Click on "View" to explore a print further.'
    context['curr_page'] = page
    context['sorting'] = 'authors'
    if sort_by != 'authors':
        context['sorting'] = sort_by

    context['sort_options'] = Page.SORT_OPTIONS
    context['filter_options'] = [("chinea", "chinea"), ("All", "all"), ("Non-Chinea", "not"), ("Buonanno", "buonanno")]

    print_list = Print.find_prints(collection)
    context['num_results'] = len(print_list)

    print_list = sorted(print_list, key=itemgetter(sort_by,'authors','title','date'))
    for i, p in enumerate(print_list):
        p['number_in_list'] = i+1
    context['print_list'] = print_list

    prints_per_page=20
    context['results_per_page'] = prints_per_page
    PAGIN = Paginator(print_list, prints_per_page)
    context['num_pages'] = PAGIN.num_pages
    context['page_range'] = PAGIN.page_range
    context['PAGIN'] = PAGIN
    page_list = []
    for i in PAGIN.page_range:
        page_list.append(PAGIN.page(i).object_list)
    context['page_list'] = page_list
    context['filter'] = collection

    return render(request, 'rome_templates/print_list.html', context)

# from django.views.decorators.clickjacking import xframe_options_exempt
# @xframe_options_exempt
def print_detail(request, print_id):
    logger.debug( '\n\nstarting print_detail()' )
    print_pid = '%s:%s' % (PID_PREFIX, print_id)
    context = std_context(request.path, )

    if request.user.is_authenticated:
        context['create_annotation_link'] = reverse('new_print_annotation', kwargs={'print_id':print_id})

    prints_list_page = request.GET.get('prints_list_page', None)
    collection = request.GET.get('collection', None)

    context['book_mode'] = 0
    context['print_mode'] = 1
    context['det_img_view_src'] = zoom_viewer_url(print_pid)
    if prints_list_page:
        context['back_to_print_href'] = u'%s?page=%s&collection=%s' % (reverse('prints'), prints_list_page, collection)
    else:
        context['back_to_print_href'] = reverse('prints')

    context['print_id'] = print_id
    context['studio_url'] = 'https://%s/studio/item/%s/' % (BDR_SERVER, print_pid)

    json_uri = 'https://%s/api/items/%s/' % (BDR_SERVER, print_pid)
    try:
        r = _fetch_url_content(json_uri)
    except Exception:
        return HttpResponseServerError('error retrieving content')
    print_json = json.loads(r.text)
    context['short_title'] = print_json['brief']['title']
    context['title'] = get_full_title_static(print_json)
    try:
        author_list=print_json['contributor_display']
        authors=""
        for i in range(len(author_list)):
            if i==len(author_list)-1:
                authors+=author_list[i]
            else:
                authors+=author_list[i]+"; "
        context['authors']=authors
    except Exception:
        context['authors']="contributor(s) not available"
    try:
        context['date'] = print_json['dateIssued'][0:4]
    except Exception:
        try:
            context['date']=print_json['dateCreated'][0:4]
        except Exception:
            context['date']="n.d."

    # annotations/metadata
    annotations=print_json['relations']['hasAnnotation']
    context['has_annotations']=len(annotations)
    context['annotation_uris']=[]
    context['annotations']=[]
    for annotation in annotations:
        annot_xml_uri = annotation_xml_url(annotation['pid'])
        context['annotation_uris'].append(annot_xml_uri)
        annotation['xml_uri'] = annot_xml_uri
        anno_id = annotation['pid'].split(':')[-1]
        if request.user.is_authenticated:
            link = reverse('edit_print_annotation', kwargs={'print_id': print_id, 'anno_id': anno_id})
            annotation['edit_link'] = link
        curr_annot = get_annotation_detail(annotation)
        context['annotations'].append(curr_annot)

    context['breadcrumbs'][-1]['name'] = breadcrumb_detail(context, view="print")
    logger.debug( f'context, ``{pprint.pformat(context)}``' )
    return render(request, 'rome_templates/page_detail.html', context)


def biography_detail(request, trp_id):
    logger.debug( '\n\nstarting biography_detail()' )
    #view that pull bio information from the db, instead of the BDR
    trp_id = "%04d" % int(trp_id)
    logger.debug( f'trp_id, ``{trp_id}``' )
    try:
        bio = Biography.objects.get(trp_id=trp_id)
        logger.debug( f'bio found in db lookup, ``{bio}``' )
    except ObjectDoesNotExist:
        logger.debug( f'bio not found' )
        return HttpResponseNotFound('Person %s Not Found' % trp_id)
    context = std_context(request.path, title="The Theater that was Rome - Biography")
    logger.debug( f'initial context, ``{pprint.pformat(context)}``' )
    context['bio'] = bio
    logger.debug( 'added bio to context' )
    context['trp_id'] = trp_id
    logger.debug( 'added trp_id to context' )
    # try:
    #     logger.debug( 'about to try bio.books() call' )
    #     context['books'] = bio.books()
    # except Exception as e:
    #     logger.exception( f'exception getting bio.books(), ``{e}``' )
    logger.debug( 'about to try bio.books() call' )
    context['books'] = bio.books()  # weird: raises error on bdr-api lookup 404
    logger.debug( f'context after bio.books() lookup, ``{pprint.pformat(context)}``' )
    context['essays'] = bio.related_essays()
    logger.debug( f'context so far, ``{pprint.pformat(context)}``' )
    prints_search = bio.prints()
    logger.debug( f'prints_search, ``{prints_search}``' )

    # Pages related to the person by annotation
    logger.debug( 'about to call annotations_by_books_and_prints()' )
    (pages_books, prints_mentioned) = annotations_by_books_and_prints(bio.name)
    logger.debug( f'pages_books, ``{pages_books}``; prints_mentioned, ``{prints_mentioned}``' )
    context['pages_books'] = pages_books
    # merge the two lists of prints
    prints_merged = [x for x in prints_mentioned if x not in prints_search]
    prints_merged[len(prints_merged):] = prints_search

    context['prints'] = prints_merged
    context['breadcrumbs'][-1]['name'] = breadcrumb_detail(context, view="bio")
    logger.debug( f'context, ``{pprint.pformat(context)}``' )
    return render(request, 'rome_templates/biography_detail.html', context)


def _get_book_pid_from_page_pid( page_pid: str ) -> str:
    logger.debug( f'starting _get_book_pid_from_page_pid() for page_pid, ``{page_pid}``' )
    query = u'https://%s/api/items/%s/' % (BDR_SERVER, page_pid)
    r = _fetch_url_content(query)
    data = json.loads(r.text)
    if data['relations']['isPartOf']:
        return data['relations']['isPartOf'][0]['pid']
    elif data['relations']['isMemberOf']:
        return data['relations']['isMemberOf'][0]['pid']
    else:
        # return None
        return ''


def filter_bios(fq, bio_list):
    logger.debug( f'starting filter_bios()' )
    return [b for b in bio_list if (b.roles and fq in b.roles)]


def biography_list(request):
    logger.debug( '\n\nstarting biography_list()' )
    fq = request.GET.get('filter', 'all')

    bio_list = Biography.objects.all()
    logger.debug( f'bio_list, ``{pprint.pformat(bio_list)}``' )

    role_set = set()

    for bio in bio_list:
        if bio.roles:
            bio.roles = [role.strip(" ") for role in bio.roles.split(';') if role.strip(" ") != '']
            role_set |= set(bio.roles)
    logger.debug( f'role_set, ``{pprint.pformat(role_set)}``' )

    if fq != 'all':
        bio_list = filter_bios(fq, bio_list)

    bios_per_page=30
    PAGIN=Paginator(bio_list,bios_per_page)
    page_list=[]

    for i in PAGIN.page_range:
        page_list.append(PAGIN.page(i).object_list)

    context=std_context(request.path, title="The Theater that was Rome - Biographies")
    context['page_documentation']='Browse the biographies of artists related to the Theater that was Rome collection.'
    context['num_results']=len(bio_list)
    context['bio_list']=bio_list
    context['results_per_page']=bios_per_page
    context['num_pages']=PAGIN.num_pages
    context['page_range']=PAGIN.page_range
    context['curr_page']=1
    context['PAGIN']=PAGIN
    context['page_list']=page_list
    context['filter_options'] = [("all","all")]
    context['filter_options'].extend([(x, x) for x in sorted(role_set)])
    context['filter'] = fq

    logger.debug( f'context, ``{pprint.pformat(context)}``' )
    return render(request, 'rome_templates/biography_list.html', context)


def links(request):
    logger.debug( '\n\nstarting links()' )
    context = std_context(request.path, style="rome/css/links.css")
    try:
        links = Static.objects.get(title="Links")
    except ObjectDoesNotExist:
        return HttpResponseNotFound('Static Links Not Found')
    context['link_text'] = links.text
    context['link_title'] = links.title
    return render(request, 'rome_templates/links.html', context)

def shops(request):
    logger.debug( '\n\nstarting shops()' )
    context = std_context(request.path, style="rome/css/links.css")
    try:
        shops = Static.objects.get(title="Shops")
    except ObjectDoesNotExist:
        return HttpResponseNotFound('Static Links Not Found')
    context['shops_text'] = shops.text
    context['shops_title'] = shops.title
    return render(request, 'rome_templates/shops.html', context)

def shop_list(request):
    logger.debug( '\n\nstarting shop_list()' )
    context=std_context(request.path, style="rome/css/links.css")
    shop_objs = Shop.objects.order_by('family')
    family_set = set()

    for shop in shop_objs:
        if shop.family:
            shop.family = [family.strip(" ") for family in shop.family.split(';') if family.strip(" ") != '']
            family_set |= set(shop.family)

    context['shop_objs'] = shop_objs
    context['num_results']= len(shop_objs)
    context['results_per_page'] = len(shop_objs)
    page = request.GET.get('page', 1)
    context['curr_page'] = page
    return render(request, 'rome_templates/shop_list.html', context)

def shop_detail(request, shop_slug):
    logger.debug( '\n\nstarting shop_detail()' )
    try:
        shop = Shop.objects.get(slug=shop_slug)
    except ObjectDoesNotExist:
        return HttpResponseNotFound('Shop %s Not Found' % shop_slug)
    context=std_context(request.path, style="rome/css/essays.css")
    context['shop_text'] = shop.text
    context['shop'] = shop
    context['people'] = shop.people.all()
    context['documents'] = shop.documents.all()
    related_list=[]
    thumbnails_list=[]
    for work in shop.related_works():
        current_work={}
        current_work['sibling'] = False
        current_work['title']=work['primary_title']
        if work.get('creator'):
            current_work['creator']=work.get('creator')[0]
        else:
            current_work['creator']="None"
        if 'genre' in work:
            current_work['genre']=work['genre'][0]
        current_work['pid']=work['pid'].split(":")[-1]
        if 'rel_is_part_of_ssim' in work:
            current_work['ppid'] = work['rel_is_part_of_ssim'][0].split(":")[-1]
        for work in related_list:
            if ('ppid' in work) and ('ppid' in current_work):
                if current_work['ppid'] == work['ppid']:
                    current_work['sibling'] = True
        if (current_work['sibling'] == False):     
            related_list.append(current_work)
        thumbnails_list.append(current_work)
    context['related_list']=related_list
    context['thumbnails_list']=thumbnails_list
    context['breadcrumbs'][-1]['name'] = shop.title
    return render(request, 'rome_templates/shop_detail.html', context)

def essay_list(request):
    logger.debug( '\n\nstarting essay_list()' )
    context=std_context(request.path, style="rome/css/links.css")
    context['page_documentation']='Listed below are essays on topics that relate to the Theater that was Rome collection of books and engravings. The majority of the essays were written by students in Brown University classes that used this material, and edited by Prof. Evelyn Lincoln.'
    essay_objs = Essay.objects.all()
    context['essay_objs'] = essay_objs
    context['num_results']=len(essay_objs)
    #temporary, until i figure out how to define an ESSAYS_PER_PAGE variable
    context['results_per_page'] = len(essay_objs)
    page = request.GET.get('page', 1)
    context['curr_page'] = page
   
    for essay in essay_objs:
        essay.thumbs = []
        essay.related_list=[]
        for work in essay.related_works():
            current_work={}
            current_work['title']=work['primary_title']
            if work.get('creator'):
                current_work['creator']=work.get('creator')[0]
            else:
                current_work['creator']="None"
            if 'genre' in work:
                current_work['genre']=work['genre'][0]
            current_work['pid']=work['pid'].split(":")[-1]
            if 'rel_is_part_of_ssim' in work:
                current_work['ppid'] = work['rel_is_part_of_ssim'][0].split(":")[-1]
                essay.thumbs.append([current_work['ppid'], current_work['pid']])
            essay.related_list.append(current_work)
            essay.thumbs = essay.thumbs[:5]
    return render(request, 'rome_templates/essay_list.html', context)


def essay_detail(request, essay_slug):
    logger.debug( '\n\nstarting essay_detail()' )
    try:
        essay = Essay.objects.get(slug=essay_slug)
    except ObjectDoesNotExist:
        return HttpResponseNotFound('Essay %s Not Found' % essay_slug)
    context=std_context(request.path, style="rome/css/essays.css")
    context['essay_text'] = essay.text
    context['essay'] = essay
    context['people'] = essay.people.all()
    related_list=[]
    thumbnails_list=[]
    for work in essay.related_works():
        current_work={}
        current_work['sibling'] = False
        current_work['title']=work['primary_title']
        if work.get('creator'):
            current_work['creator']=work.get('creator')[0]
        else:
            current_work['creator']="None"
        if 'genre' in work:
            current_work['genre']=work['genre'][0]
        current_work['pid']=work['pid'].split(":")[-1]
        if 'rel_is_part_of_ssim' in work:
            current_work['ppid'] = work['rel_is_part_of_ssim'][0].split(":")[-1]
        for work in related_list:
            if ('ppid' in work) and ('ppid' in current_work):
                if current_work['ppid'] == work['ppid']:
                    current_work['sibling'] = True
        if (current_work['sibling'] == False):     
            related_list.append(current_work)
        thumbnails_list.append(current_work)
    context['related_list']=related_list
    context['thumbnails_list']=thumbnails_list
    context['breadcrumbs'][-1]['name'] = essay.title
    return render(request, 'rome_templates/essay_detail.html', context)

def documents(request):
    logger.debug( '\n\nstarting documents()' )
    return render(request, 'rome_templates/documents.html')


def document_detail(request, document_slug):
    logger.debug( '\n\nstarting document_detail()' )
    try:
        document = Document.objects.get(slug=document_slug)
    except ObjectDoesNotExist:
        return HttpResponseNotFound('Document %s Not Found' % document_slug)
    context = std_context(request.path, style="rome/css/essays.css")
    context['document'] = document
    context['people'] = document.people.all()
    context['breadcrumbs'][-1]['name'] = document.title
    return render(request, 'rome_templates/document_detail.html', context)


def breadcrumb_detail(context, view="book", title_words=4):
    logger.debug( f'starting non-top-level-view breadcrumb_detail()' )
    if(view == "book"):
        return " ".join(context['book'].title().split(" ")[0:title_words]) + " . . ."

    if(view == "print"):
        return " ".join(context['title'].split(" ")[0:title_words]) + " . . ."

    if(view == "bio"):
        return context['bio'].name


def search_page(request):
    logger.debug( '\n\nstarting search_page()' )
    context = std_context(request.path, style= "rome/css/links.css")
    searchquery = 'https://%s/api/search/?q=rel_is_member_of_collection_ssim:"%s"+object_type:annotation+display:BDR_PUBLIC' % (BDR_SERVER, settings.TTWR_COLLECTION_PID)
    thumbnailquery = "https://%s/viewers/image/thumbnail/" % (BDR_SERVER)
    pagequery = "https://%s/api/items/" % (BDR_SERVER)
    context["searchquery"] = searchquery
    context["thumbnailquery"] = thumbnailquery
    context["pagequery"] = pagequery
    return render(request, 'rome_templates/search_page.html', context)


@login_required(login_url=reverse_lazy('rome_login'))
def new_annotation(request, book_id, page_id):
    logger
    page_pid = '%s:%s' % (PID_PREFIX, page_id)
    from .forms import AnnotationForm, PersonForm, InscriptionForm
    PersonFormSet = formset_factory(PersonForm)
    InscriptionFormSet = formset_factory(InscriptionForm)
    if request.method == 'POST':
        form = AnnotationForm(request.POST)
        person_formset = PersonFormSet(request.POST, prefix='people')
        inscription_formset = InscriptionFormSet(request.POST, prefix='inscriptions')
        if form.is_valid() and person_formset.is_valid() and inscription_formset.is_valid():
            if request.user.first_name:
                annotator = u'%s %s' % (request.user.first_name, request.user.last_name)
            else:
                annotator = u'%s' % request.user.username
            annotation = Annotation.from_form_data(page_pid, annotator, form.cleaned_data, person_formset.cleaned_data, inscription_formset.cleaned_data)
            try:
                response = annotation.save_to_bdr()
                logger.info('%s added annotation %s for %s' % (request.user.username, response['pid'], page_id))
                return HttpResponseRedirect(reverse('book_page_viewer', kwargs={'book_id': book_id, 'page_id': page_id}))
            except Exception as e:
                logger.error('error saving new annotation:')
                import traceback
                logger.error(traceback.format_exc())
                return HttpResponseServerError('Internal server error. Check log.')
    else:
        inscription_formset = InscriptionFormSet(prefix='inscriptions')
        person_formset = PersonFormSet(prefix='people')
        form = AnnotationForm()

    image_link = zoom_viewer_url(page_pid)
    return render(request, 'rome_templates/new_annotation.html',
            {'form': form, 'person_formset': person_formset, 'inscription_formset': inscription_formset, 'image_link': image_link})


@login_required(login_url=reverse_lazy('rome_login'))
def new_print_annotation(request, print_id):
    logger.debug( '\n\nstarting new_print_annotation()' )
    print_pid = '%s:%s' % (PID_PREFIX, print_id)
    from .forms import AnnotationForm, PersonForm, InscriptionForm
    PersonFormSet = formset_factory(PersonForm)
    InscriptionFormSet = formset_factory(InscriptionForm)
    if request.method == 'POST':
        form = AnnotationForm(request.POST)
        person_formset = PersonFormSet(request.POST, prefix='people')
        inscription_formset = InscriptionFormSet(request.POST, prefix='inscriptions')
        if form.is_valid() and person_formset.is_valid() and inscription_formset.is_valid():
            if request.user.first_name:
                annotator = u'%s %s' % (request.user.first_name, request.user.last_name)
            else:
                annotator = u'%s' % request.user.username
            annotation = Annotation.from_form_data(print_pid, annotator, form.cleaned_data, person_formset.cleaned_data, inscription_formset.cleaned_data)
            try:
                response = annotation.save_to_bdr()
                logger.info('%s added annotation %s for %s' % (request.user.username, response['pid'], print_id))
                return HttpResponseRedirect(reverse('specific_print', kwargs={'print_id': print_id}))
            except Exception as e:
                logger.error(str(e))
                return HttpResponseServerError('Internal server error. Check log.')
    else:
        inscription_formset = InscriptionFormSet(prefix='inscriptions')
        person_formset = PersonFormSet(prefix='people')
        form = AnnotationForm()

    image_link = zoom_viewer_url(print_pid)
    return render(request, 'rome_templates/new_annotation.html',
            {'form': form, 'person_formset': person_formset, 'inscription_formset': inscription_formset, 'image_link': image_link})


def get_bound_edit_forms(annotation, AnnotationForm, PersonFormSet, InscriptionFormSet):
    logger.debug( 'starting non-top-level-view get_bound_edit_forms()' )
    person_formset = PersonFormSet(initial=annotation.get_person_formset_data(), prefix='people')
    inscription_formset = InscriptionFormSet(initial=annotation.get_inscription_formset_data(), prefix='inscriptions')
    form = AnnotationForm(annotation.get_form_data())
    return {'form': form, 'person_formset': person_formset, 'inscription_formset': inscription_formset}


def edit_annotation_base(request, image_pid, anno_pid, redirect_url):
    logger.debug( '\n\nstarting edit_annotation_base()' )
    from .forms import AnnotationForm, PersonForm, InscriptionForm
    PersonFormSet = formset_factory(PersonForm)
    InscriptionFormSet = formset_factory(InscriptionForm)
    context_data = {}
    annotation = Annotation.from_pid(anno_pid)
    if request.method == 'POST':
        #this part here is similar to posting a new annotation
        form = AnnotationForm(request.POST)
        person_formset = PersonFormSet(request.POST, prefix='people')
        inscription_formset = InscriptionFormSet(request.POST, prefix='inscriptions')
        if form.is_valid() and person_formset.is_valid() and inscription_formset.is_valid():
            #update the annotator to be the person making this edit
            if request.user.first_name:
                annotator = u'%s %s' % (request.user.first_name, request.user.last_name)
            else:
                annotator = u'%s' % request.user.username
            annotation.add_form_data(annotator, form.cleaned_data, person_formset.cleaned_data, inscription_formset.cleaned_data)
            try:
                response = annotation.update_in_bdr()
                logger.info('%s edited annotation %s' % (request.user.username, anno_pid))
                return HttpResponseRedirect(redirect_url)
            except Exception as e:
                logger.error(str(e))
                return HttpResponseServerError('Internal server error. Check log.')
        else:
            context_data.update({'form': form, 'person_formset': person_formset, 'inscription_formset': inscription_formset})
    else:
        try:
            context_data.update(get_bound_edit_forms(annotation, AnnotationForm, PersonFormSet, InscriptionFormSet))
        except InvalidNameError as e:
            mail_admins(subject='TTWR create/edit annotation error',
                    message=f'exception: {e}', fail_silently=False)
            return HttpResponse('Existing annotation is invalid. Email has been sent to bdr@brown.edu.')
        except Exception as e:
            logger.error('loading data to edit %s: %s' % (anno_pid, e))
            import traceback
            logger.error(traceback.format_exc())
            return HttpResponseServerError('Internal server error.')

    image_link = zoom_viewer_url(image_pid)
    context_data.update({'image_link': image_link})
    return render(request, 'rome_templates/new_annotation.html', context_data)


@login_required(login_url=reverse_lazy('rome_login'))
def edit_annotation(request, book_id, page_id, anno_id):
    logger.debug( '\n\nstarting edit_annotation()' )
    anno_pid = '%s:%s' % (PID_PREFIX, anno_id)
    page_pid = '%s:%s' % (PID_PREFIX, page_id)
    return edit_annotation_base(request, page_pid, anno_pid, reverse('book_page_viewer', kwargs={'book_id': book_id, 'page_id': page_id}))


@login_required(login_url=reverse_lazy('rome_login'))
def edit_print_annotation(request, print_id, anno_id):
    logger.debug( '\n\nstarting edit_print_annotation()' )
    anno_pid = '%s:%s' % (PID_PREFIX, anno_id)
    print_pid = '%s:%s' % (PID_PREFIX, print_id)
    return edit_annotation_base(request, print_pid, anno_pid, reverse('specific_print', kwargs={'print_id': print_id}))


@login_required(login_url=reverse_lazy('rome_login'))
def new_genre(request):
    logger.debug( '\n\nstarting new_genre()' )
    from .forms import NewGenreForm
    if request.method == 'POST':
        form = NewGenreForm(request.POST)
        if form.is_valid():
            genre = form.save()
            return SimpleTemplateResponse('rome_templates/popup_response.html', {
                            'pk_value': escape(genre._get_pk_val()),
                            'value': escape(genre.serializable_value(genre._meta.pk.attname)),
                            'obj': escapejs(genre)})
    else:
        form = NewGenreForm()

    return render(request, 'rome_templates/new_record.html', {'form': form})


@login_required(login_url=reverse_lazy('rome_login'))
def new_role(request):
    logger.debug( '\n\nstarting new_role()' )
    from .forms import NewRoleForm
    if request.method == 'POST':
        form = NewRoleForm(request.POST)
        if form.is_valid():
            role = form.save()
            return SimpleTemplateResponse('rome_templates/popup_response.html', {
                            'pk_value': escape(role._get_pk_val()),
                            'value': escape(role.serializable_value(role._meta.pk.attname)),
                            'obj': escapejs(role)})
    else:
        form = NewRoleForm()

    #use the same template for genre and role
    return render(request, 'rome_templates/new_record.html', {'form': form})


@login_required(login_url=reverse_lazy('rome_login'))
def new_biography(request):
    logger.debug( '\n\nstarting new_biography()' )
    from .forms import NewBiographyForm
    if request.method == 'POST':
        form = NewBiographyForm(request.POST)
        if form.is_valid():
            bio = form.save()
            return SimpleTemplateResponse('rome_templates/popup_response.html', {
                            'pk_value': escape(bio._get_pk_val()),
                            'value': escape(bio.serializable_value(bio._meta.pk.attname)),
                            'obj': escapejs(bio)})
    else:
        form = NewBiographyForm()

    #use the same template for genre and role
    return render(request, 'rome_templates/new_record.html', {'form': form})


def _get_prev_next_ids(book_json, page_pid):
    logger.debug( f'starting non-top-level-view _get_prev_next_ids()' )
    prev_id = "none"
    next_id = "none"
    for index, page in enumerate(book_json['relations']['hasPart']):
        if page['pid'] == page_pid:
            try:
                prev_id = book_json['relations']['hasPart'][index - 1]['pid'].split(":")[-1]
            except (KeyError, IndexError):
                pass
            try:
                next_id = book_json['relations']['hasPart'][index + 1]['pid'].split(":")[-1]
            except (KeyError, IndexError):
                pass
    return (prev_id, next_id)


def version( request ):
    """ Returns basic branch and commit data. """
    logger.debug( '\n\nstarting version()' )
    rq_now = datetime.datetime.now()
    gatherer = GatherCommitAndBranchData()
    trio.run( gatherer.manage_git_calls )
    commit = gatherer.commit
    branch = gatherer.branch
    info_txt = commit.replace( 'commit', branch )
    context = version_helper.make_context( request, rq_now, info_txt )
    output = json.dumps( context, sort_keys=True, indent=2 )
    logger.debug( f'output, ``{output}``' )
    return HttpResponse( output, content_type='application/json; charset=utf-8' )
