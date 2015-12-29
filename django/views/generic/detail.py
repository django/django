from __future__ import unicode_literals

from django.core.exceptions import ImproperlyConfigured
from django.db import models
from django.http import Http404
from django.utils.translation import ugettext as _
from django.views.generic.base import ContextMixin, TemplateResponseMixin, View


class SingleObjectMixin(ContextMixin):
    """
    Provides the ability to retrieve a single object for further manipulation.
    """
    model = None
    queryset = None
    slug_field = 'slug'
    context_object_name = None
    slug_url_kwarg = 'slug'
    pk_url_kwarg = 'pk'
    query_pk_and_slug = False

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

        # Next, try looking up by primary key.
        pk = self.kwargs.get(self.pk_url_kwarg)
        slug = self.kwargs.get(self.slug_url_kwarg)
        if pk is not None:
            queryset = queryset.filter(pk=pk)

        # Next, try looking up by slug.
        if slug is not None and (pk is None or self.query_pk_and_slug):
            slug_field = self.get_slug_field()
            queryset = queryset.filter(**{slug_field: slug})

        # If none of those are defined, it's an error.
        if pk is None and slug is None:
            raise AttributeError("Generic detail view %s must be called with "
                                 "either an object pk or a slug."
                                 % self.__class__.__name__)

        try:
            # Get the single item from the filtered queryset
            obj = queryset.get()
        except queryset.model.DoesNotExist:
            raise Http404(_("No %(verbose_name)s found matching the query") %
                          {'verbose_name': queryset.model._meta.verbose_name})
        return obj

    def get_queryset(self):
        """
        Return the `QuerySet` that will be used to look up the object.

        Note that this method is called by the default implementation of
        `get_object` and may not be called if `get_object` is overridden.
        """
        if self.queryset is None:
            if self.model:
                return self.model._default_manager.all()
            else:
                raise ImproperlyConfigured(
                    "%(cls)s is missing a QuerySet. Define "
                    "%(cls)s.model, %(cls)s.queryset, or override "
                    "%(cls)s.get_queryset()." % {
                        'cls': self.__class__.__name__
                    }
                )
        return self.queryset.all()

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
            if self.object._deferred:
                obj = obj._meta.proxy_for_model
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

        * the contents of the ``template_name_field`` field on the
          object instance that the view is operating upon (if available)
        * the value of ``template_name`` on the view (if provided)
        * ``<app_label>/<model_name><template_name_suffix>.html`` from the model obtained
          from ``self.object`` or ``self.model`` (if available)
        """
        try:
            names = super(SingleObjectTemplateResponseMixin, self).get_template_names()
        except ImproperlyConfigured:
            # If template_name isn't specified, it's not a problem --
            # we just start with an empty list.
            names = []

        # The most specific option is if self.template_name_field is set, grab the
        # value of the field of that name from the object.
        if hasattr(self, 'object') and self.object and self.template_name_field:
            name = getattr(self.object, self.template_name_field, None)
            if name:
                names.insert(0, name)

        # The least-specific option is the default <app>/<model>_detail.html;
        # only use this if the object in question is a model.
        if hasattr(self, 'object') and isinstance(self.object, models.Model):
            object_meta = self.object._meta
            if self.object._deferred:
                object_meta = self.object._meta.proxy_for_model._meta
        elif hasattr(self, 'model') and self.model is not None and issubclass(self.model, models.Model):
            object_meta = self.model._meta
        else:
            object_meta = None
        if object_meta is not None:
            names.append("%s/%s%s.html" % (
                object_meta.app_label,
                object_meta.model_name,
                self.template_name_suffix
            ))

        if not names:
            # If we still haven't managed to find any template names, we should
            # raise ImproperlyConfigured to alert the developer.
            raise ImproperlyConfigured(
                "SingleObjectTemplateResponseMixin requires either a definition of "
                "'template_name', an implementation of 'get_template_names()', "
                "a non-empty 'template_name_field' on the object, "
                "self.object is an instance of models.Model, "
                "or a definition of 'model'.")

        return names


class DetailView(SingleObjectTemplateResponseMixin, BaseDetailView):
    """
    Render a "detail" view of an object.

    By default this is a model instance looked up from `self.queryset`, but the
    view will support display of *any* object by overriding `self.get_object()`.
    """
