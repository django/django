import warnings

from django.http import HttpResponse
from django.template import Context, RequestContext, Template, loader
from django.template.backends.django import Template as BackendTemplate
from django.template.context import _current_app_undefined
from django.utils import six
from django.utils.deprecation import RemovedInDjango20Warning


class ContentNotRenderedError(Exception):
    pass


class SimpleTemplateResponse(HttpResponse):
    rendering_attrs = ['template_name', 'context_data', '_post_render_callbacks']

    def __init__(self, template, context=None, content_type=None, status=None,
                 charset=None, using=None):
        if isinstance(template, Template):
            warnings.warn(
                "{}'s template argument cannot be a django.template.Template "
                "anymore. It may be a backend-specific template like those "
                "created by get_template().".format(self.__class__.__name__),
                RemovedInDjango20Warning, stacklevel=2)
            template = BackendTemplate(template)

        # It would seem obvious to call these next two members 'template' and
        # 'context', but those names are reserved as part of the test Client
        # API. To avoid the name collision, we use different names.
        self.template_name = template
        self.context_data = context

        self.using = using

        self._post_render_callbacks = []

        # _request stores the current request object in subclasses that know
        # about requests, like TemplateResponse. It's defined in the base class
        # to minimize code duplication.
        # It's called self._request because self.request gets overwritten by
        # django.test.client.Client. Unlike template_name and context_data,
        # _request should not be considered part of the public API.
        self._request = None

        # content argument doesn't make sense here because it will be replaced
        # with rendered template so we always pass empty string in order to
        # prevent errors and provide shorter signature.
        super(SimpleTemplateResponse, self).__init__('', content_type, status, charset)

        # _is_rendered tracks whether the template and context has been baked
        # into a final response.
        # Super __init__ doesn't know any better than to set self.content to
        # the empty string we just gave it, which wrongly sets _is_rendered
        # True, so we initialize it to False after the call to super __init__.
        self._is_rendered = False

    def __getstate__(self):
        """Pickling support function.

        Ensures that the object can't be pickled before it has been
        rendered, and that the pickled state only includes rendered
        data, not the data used to construct the response.
        """
        obj_dict = self.__dict__.copy()
        if not self._is_rendered:
            raise ContentNotRenderedError('The response content must be '
                                          'rendered before it can be pickled.')
        for attr in self.rendering_attrs:
            if attr in obj_dict:
                del obj_dict[attr]

        return obj_dict

    def resolve_template(self, template):
        "Accepts a template object, path-to-template or list of paths"
        if isinstance(template, (list, tuple)):
            return loader.select_template(template, using=self.using)
        elif isinstance(template, six.string_types):
            return loader.get_template(template, using=self.using)
        else:
            return template

    def _resolve_template(self, template):
        # This wrapper deprecates returning a django.template.Template in
        # subclasses that override resolve_template. It can be removed in
        # Django 2.0.
        new_template = self.resolve_template(template)
        if isinstance(new_template, Template):
            warnings.warn(
                "{}.resolve_template() must return a backend-specific "
                "template like those created by get_template(), not a "
                "{}.".format(
                    self.__class__.__name__, new_template.__class__.__name__),
                RemovedInDjango20Warning, stacklevel=2)
            new_template = BackendTemplate(new_template)
        return new_template

    def resolve_context(self, context):
        return context

    def _resolve_context(self, context):
        # This wrapper deprecates returning a Context or a RequestContext in
        # subclasses that override resolve_context. It can be removed in
        # Django 2.0. If returning a Context or a RequestContext works by
        # accident, it won't be an issue per se, but it won't be officially
        # supported either.
        new_context = self.resolve_context(context)
        if isinstance(new_context, RequestContext) and self._request is None:
            self._request = new_context.request
        if isinstance(new_context, Context):
            warnings.warn(
                "{}.resolve_context() must return a dict, not a {}.".format(
                    self.__class__.__name__, new_context.__class__.__name__),
                RemovedInDjango20Warning, stacklevel=2)
            # It would be tempting to do new_context = new_context.flatten()
            # here but that would cause template context processors to run for
            # TemplateResponse(request, template, Context({})), which would be
            # backwards-incompatible. As a consequence another deprecation
            # warning will be raised when rendering the template. There isn't
            # much we can do about that.
        return new_context

    @property
    def rendered_content(self):
        """Returns the freshly rendered content for the template and context
        described by the TemplateResponse.

        This *does not* set the final content of the response. To set the
        response content, you must either call render(), or set the
        content explicitly using the value of this property.
        """
        template = self._resolve_template(self.template_name)
        context = self._resolve_context(self.context_data)
        content = template.render(context, self._request)
        return content

    def add_post_render_callback(self, callback):
        """Adds a new post-rendering callback.

        If the response has already been rendered,
        invoke the callback immediately.
        """
        if self._is_rendered:
            callback(self)
        else:
            self._post_render_callbacks.append(callback)

    def render(self):
        """Renders (thereby finalizing) the content of the response.

        If the content has already been rendered, this is a no-op.

        Returns the baked response instance.
        """
        retval = self
        if not self._is_rendered:
            self.content = self.rendered_content
            for post_callback in self._post_render_callbacks:
                newretval = post_callback(retval)
                if newretval is not None:
                    retval = newretval
        return retval

    @property
    def is_rendered(self):
        return self._is_rendered

    def __iter__(self):
        if not self._is_rendered:
            raise ContentNotRenderedError('The response content must be '
                                          'rendered before it can be iterated over.')
        return super(SimpleTemplateResponse, self).__iter__()

    @property
    def content(self):
        if not self._is_rendered:
            raise ContentNotRenderedError('The response content must be '
                                          'rendered before it can be accessed.')
        return super(SimpleTemplateResponse, self).content

    @content.setter
    def content(self, value):
        """Sets the content for the response
        """
        HttpResponse.content.fset(self, value)
        self._is_rendered = True


class TemplateResponse(SimpleTemplateResponse):
    rendering_attrs = SimpleTemplateResponse.rendering_attrs + ['_request', '_current_app']

    def __init__(self, request, template, context=None, content_type=None,
            status=None, current_app=_current_app_undefined, charset=None,
            using=None):
        # As a convenience we'll allow callers to provide current_app without
        # having to avoid needing to create the RequestContext directly
        if current_app is not _current_app_undefined:
            warnings.warn(
                "The current_app argument of TemplateResponse is deprecated. "
                "Set the current_app attribute of its request instead.",
                RemovedInDjango20Warning, stacklevel=2)
            request.current_app = current_app
        super(TemplateResponse, self).__init__(
            template, context, content_type, status, charset, using)
        self._request = request
