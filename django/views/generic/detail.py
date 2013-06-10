from __future__ import unicode_literals

from django.core.exceptions import ImproperlyConfigured, ObjectDoesNotExist
from django.db import models
from django.http import Http404
from django.utils.translation import ugettext as _
from django.views.generic.base import TemplateResponseMixin, ContextMixin, View
import warnings


class SingleObjectMixin(ContextMixin):
    """
    Provides the ability to retrieve a single object for further manipulation.
    """
    model = None
    queryset = None
    context_object_name = None
    lookup_field = 'pk'

    # The following are pending deprecation
    slug_field = 'slug'
    slug_url_kwarg = 'slug'
    pk_url_kwarg = 'pk'

    def get_object(self, queryset=None):
        """
        Returns the object the view is displaying.

        By default this requires `self.queryset` and a `pk` or `slug` argument
        in the URLconf, but subclasses can override this to return any object.
        """
        # Use a custom queryset if provided; this is required for subclasses
        # like DateDetailView
        if queryset is None:
            queryset = self.get_queryset()

        lookup = self.kwargs.get(self.lookup_field)
        pk = self.kwargs.get(self.pk_url_kwarg)
        slug = self.kwargs.get(self.slug_url_kwarg)

        # Try looking up by whichever field is specified in `lookup_field`.
        if lookup is not None:
            queryset = queryset.filter(**{self.lookup_field: lookup})

        # Next, try looking up by primary key.  Note that we only attempt this
        # deprecated lookup style if `lookup_field` has not been explicitly set.
        elif pk is not None and self.lookup_field == 'pk':
            warnings.warn(
                "Usage of `pk_url_kwarg` is pending deprecation. "
                "Set `lookup_field` on the '%s' view instead." %
                self.__class__.__name__,
                PendingDeprecationWarning)
            queryset = queryset.filter(pk=pk)

        # Next, try looking up by slug.  Note that we only attempt this
        # deprecated lookup style if `lookup_field` has not been explicitly set.
        elif slug is not None and self.lookup_field == 'pk':
            warnings.warn(
                "Usage of `slug_field` and/or `slug_url_kwarg` is pending "
                "deprecation. Set `lookup_field` on the '%s' view instead." %
                self.__class__.__name__,
                PendingDeprecationWarning)
            slug_field = self.get_slug_field()
            queryset = queryset.filter(**{slug_field: slug})

        # If none of those are defined, it's an error.
        else:
            raise AttributeError("Generic detail view %s uses lookup field "
                                 "'%s', which was not passed by the URL conf."
                                 % (self.__class__.__name__, self.lookup_field))

        try:
            # Get the single item from the filtered queryset
            obj = queryset.get()
        except ObjectDoesNotExist:
            raise Http404(_("No %(verbose_name)s found matching the query") %
                          {'verbose_name': queryset.model._meta.verbose_name})
        return obj

    def get_queryset(self):
        """
        Get the queryset to look an object up against. May not be called if
        `get_object` is overridden.
        """
        if self.queryset is None:
            if self.model:
                return self.model._default_manager.all()
            else:
                raise ImproperlyConfigured("%(cls)s is missing a queryset. Define "
                                           "%(cls)s.model, %(cls)s.queryset, or override "
                                           "%(cls)s.get_queryset()." % {
                                                'cls': self.__class__.__name__
                                        })
        return self.queryset._clone()

    def get_slug_field(self):
        """
        Get the name of a slug field to be used to look up by slug.
        """
        return self.slug_field

    def get_context_object_name(self, obj):
        """
        Get the name to use for the object.
        """
        if self.context_object_name:
            return self.context_object_name
        elif isinstance(obj, models.Model):
            return obj._meta.model_name
        else:
            return None

    def get_context_data(self, **kwargs):
        """
        Insert the single object into the context dict.
        """
        context = {}
        if self.object:
            context['object'] = self.object
            context_object_name = self.get_context_object_name(self.object)
            if context_object_name:
                context[context_object_name] = self.object
        context.update(kwargs)
        return super(SingleObjectMixin, self).get_context_data(**context)


class BaseDetailView(SingleObjectMixin, View):
    """
    A base view for displaying a single object
    """
    def get(self, request, *args, **kwargs):
        self.object = self.get_object()
        context = self.get_context_data(object=self.object)
        return self.render_to_response(context)


class SingleObjectTemplateResponseMixin(TemplateResponseMixin):
    template_name_field = None
    template_name_suffix = '_detail'

    def get_template_names(self):
        """
        Return a list of template names to be used for the request. May not be
        called if render_to_response is overridden. Returns the following list:

        * the value of ``template_name`` on the view (if provided)
        * the contents of the ``template_name_field`` field on the
          object instance that the view is operating upon (if available)
        * ``<app_label>/<object_name><template_name_suffix>.html``
        """
        try:
            names = super(SingleObjectTemplateResponseMixin, self).get_template_names()
        except ImproperlyConfigured:
            # If template_name isn't specified, it's not a problem --
            # we just start with an empty list.
            names = []

        # If self.template_name_field is set, grab the value of the field
        # of that name from the object; this is the most specific template
        # name, if given.
        if self.object and self.template_name_field:
            name = getattr(self.object, self.template_name_field, None)
            if name:
                names.insert(0, name)

        # The least-specific option is the default <app>/<model>_detail.html;
        # only use this if the object in question is a model.
        if isinstance(self.object, models.Model):
            names.append("%s/%s%s.html" % (
                self.object._meta.app_label,
                self.object._meta.model_name,
                self.template_name_suffix
            ))
        elif hasattr(self, 'model') and self.model is not None and issubclass(self.model, models.Model):
            names.append("%s/%s%s.html" % (
                self.model._meta.app_label,
                self.model._meta.model_name,
                self.template_name_suffix
            ))
        return names


class DetailView(SingleObjectTemplateResponseMixin, BaseDetailView):
    """
    Render a "detail" view of an object.

    By default this is a model instance looked up from `self.queryset`, but the
    view will support display of *any* object by overriding `self.get_object()`.
    """
