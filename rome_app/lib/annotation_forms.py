import logging

from django.contrib.auth.models import User
from django.core.exceptions import PermissionDenied
from django.core.mail import mail_admins
from django.forms.formsets import formset_factory
from django.http import HttpRequest, HttpResponse, HttpResponseRedirect, HttpResponseServerError
from django.shortcuts import render

from rome_app.lib.bdr_client import BdrUnavailable
from rome_app.models import Annotation, InvalidNameError, zoom_viewer_url

logger = logging.getLogger('rome')


def get_bound_edit_forms(annotation: Annotation, AnnotationForm, PersonFormSet, InscriptionFormSet) -> dict:
    """
    Binds existing annotation values to editing forms.
    Called by: edit_annotation_base()
    """
    logger.debug('starting non-top-level-view get_bound_edit_forms()')
    person_formset = PersonFormSet(initial=annotation.get_person_formset_data(), prefix='people')
    inscription_formset = InscriptionFormSet(initial=annotation.get_inscription_formset_data(), prefix='inscriptions')
    form = AnnotationForm(annotation.get_form_data())
    return {'form': form, 'person_formset': person_formset, 'inscription_formset': inscription_formset}


def edit_annotation_base(request: HttpRequest, image_pid: str, anno_pid: str, redirect_url: str) -> HttpResponse:
    """
    Displays and saves an annotation edit form.
    Called by: views.edit_annotation(), views.edit_print_annotation()
    """
    logger.debug('\n\nstarting edit_annotation_base()')
    if not isinstance(request.user, User):
        raise PermissionDenied
    from rome_app.forms import AnnotationForm, InscriptionForm, PersonForm

    PersonFormSet = formset_factory(PersonForm)
    InscriptionFormSet = formset_factory(InscriptionForm)
    context_data = {}
    annotation = Annotation.from_pid(anno_pid)
    if request.method == 'POST':
        # this part here is similar to posting a new annotation
        form = AnnotationForm(request.POST)
        person_formset = PersonFormSet(request.POST, prefix='people')
        inscription_formset = InscriptionFormSet(request.POST, prefix='inscriptions')
        if form.is_valid() and person_formset.is_valid() and inscription_formset.is_valid():
            # update the annotator to be the person making this edit
            if request.user.first_name:
                annotator = f'{request.user.first_name} {request.user.last_name}'
            else:
                annotator = f'{request.user.username}'
            annotation.add_form_data(
                annotator, form.cleaned_data, person_formset.cleaned_data, inscription_formset.cleaned_data
            )
            try:
                annotation.update_in_bdr()
                logger.info(f'{request.user.username} edited annotation {anno_pid}')
                return HttpResponseRedirect(redirect_url)
            except BdrUnavailable:
                raise
            except Exception:
                logger.exception('error updating annotation')
                return HttpResponseServerError('Internal server error. Check log.')
        else:
            context_data.update({'form': form, 'person_formset': person_formset, 'inscription_formset': inscription_formset})
    else:
        try:
            context_data.update(get_bound_edit_forms(annotation, AnnotationForm, PersonFormSet, InscriptionFormSet))
        except InvalidNameError as e:
            mail_admins(subject='TTWR create/edit annotation error', message=f'exception: {e}', fail_silently=False)
            return HttpResponse('Existing annotation is invalid. Email has been sent to bdr@brown.edu.')
        except Exception:
            logger.exception(f'error loading annotation, ``{anno_pid}``')
            return HttpResponseServerError('Internal server error.')

    image_link = zoom_viewer_url(image_pid)
    context_data.update({'image_link': image_link})
    return render(request, 'rome_templates/new_annotation.html', context_data)
