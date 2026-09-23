import copy

from django import forms
from django.forms.renderers import BaseRenderer, get_default_renderer
from django.urls import reverse
from django.utils.safestring import SafeString, mark_safe
from django.utils.translation import gettext as _


class AddAnotherWidgetWrapper(forms.Widget):
    """ 
    This class is a wrapper to a given widget to add the add icon for the
    admin interface. Modeled after
    django.contrib.admin.widgets.RelatedFieldWidgetWrapper
    """
    def __init__(self, widget, model, related_url_name):
        self.needs_multipart_form = widget.needs_multipart_form
        self.attrs = widget.attrs
        self.choices = widget.choices
        self.widget = widget
        self.model = model
        self.related_url_name = related_url_name
 
    def __deepcopy__(self, memo):
        obj = copy.copy(self)
        obj.widget = copy.deepcopy(self.widget, memo)
        obj.attrs = self.widget.attrs
        memo[id(self)] = obj 
        return obj 
 
    @property
    def media(self):
        return self.widget.media

    def render(
        self, name: str, value: object, attrs: dict | None = None, renderer: BaseRenderer | None = None
    ) -> SafeString:
        """
        Renders a select with a labeled plus control for the existing add-another popup.
        Called by: Django BoundField rendering
        """
        self.widget.choices = self.choices
        context = {
            'widget': self.widget.render(name, value, attrs=attrs, renderer=renderer),
            'name': name,
            'related_url': reverse(self.related_url_name),
            'label': _('Add another %(model)s') % {'model': self.model._meta.verbose_name},
        }
        if renderer is None:
            renderer = get_default_renderer()
        return mark_safe(renderer.render('rome_templates/widgets/add_another.html', context))
 
    def build_attrs(self, extra_attrs=None, **kwargs):
        "Helper function for building an attribute dictionary."
        self.attrs = self.widget.build_attrs(extra_attrs=None, **kwargs)
        return self.attrs

    def value_from_datadict(self, data, files, name):
        return self.widget.value_from_datadict(data, files, name)

    def _has_changed(self, initial, data):
        return self.widget._has_changed(initial, data)

    def id_for_label(self, id_):
        return self.widget.id_for_label(id_)
