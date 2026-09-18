from django.contrib import admin
from django.urls import re_path

from rome_app import views

BDR_ID_RE = '[a-z0-9]+'


urlpatterns = [
    #admin/user
    re_path(r'^admin/', admin.site.urls),
    re_path(r'^login/$', views.login_page, name='rome_login'),
    re_path(r'^logout/$', views.logout_page, name='rome_logout'),

    #index and static
    re_path(r'^$', views.index, name='index'),
    re_path(r'^about/', views.about, name='about'),
    re_path(r'^links/$', views.links, name='links'),
    re_path(r'^shops/$', views.shops, name='shops'),

    #books, prints, essays, shops...
    re_path(r'^books/$', views.book_list, name='books'),
    re_path(fr'^books/(?P<book_id>{BDR_ID_RE})/$', views.book_detail, name='thumbnail_viewer'),
    re_path(fr'^books/(?P<book_id>{BDR_ID_RE})/(?P<page_id>{BDR_ID_RE})/$', views.page_detail, name='book_page_viewer'),
    re_path(fr'^books/(?P<book_id>{BDR_ID_RE})/(?P<page_id>{BDR_ID_RE})/annotations/new/$', views.new_annotation, name='new_annotation'),
    re_path(fr'^books/(?P<book_id>{BDR_ID_RE})/(?P<page_id>{BDR_ID_RE})/annotations/(?P<anno_id>{BDR_ID_RE})/edit/$', views.edit_annotation, name='edit_annotation'),
    re_path(r'^prints/$', views.print_list, name='prints'),
    re_path(fr'^prints/(?P<print_id>{BDR_ID_RE})/$', views.print_detail, name='specific_print'),
    re_path(fr'^prints/(?P<print_id>{BDR_ID_RE})/annotations/new/$', views.new_print_annotation, name='new_print_annotation'),
    re_path(fr'^prints/(?P<print_id>{BDR_ID_RE})/annotations/(?P<anno_id>{BDR_ID_RE})/edit/$', views.edit_print_annotation, name='edit_print_annotation'),
    re_path(r'^essays/$', views.essay_list, name='essays'),
    re_path(r'^essays/(?P<essay_slug>[\w-]+)/$', views.essay_detail, name='specific_essay'),
    re_path(r'^people/$', views.biography_list, name='people'),
    re_path(r'^people/(?P<trp_id>\d+)/$', views.biography_detail, name='person_detail'),
    re_path(r'^shop_list/$', views.shop_list, name='shop_list'),
    re_path(r'^shop_list/(?P<shop_slug>[\w-]+)/$', views.shop_detail, name='specific_shop'),
    re_path(r'^documents/$', views.documents, name='documents'),
    re_path(r'^documents/(?P<document_slug>[\w-]+)/$', views.document_detail, name='specific_document'),

    #create new records
    re_path(r'^genres/new/$', views.new_genre, name='new_genre'),
    re_path(r'^roles/new/$', views.new_role, name='new_role'),
    re_path(r'^biographies/new/$', views.new_biography, name='new_biography'),

    re_path(r'^search/$', views.search_page, name= 'search_page'),

    ## helper view
    re_path( r'^version/$', views.version, name='version_url' ),

    ## temp data-correction
    re_path( r'^temp_roles_checker/$', views.temp_roles_checker, name='temp_roles_checker_url' ),
]
