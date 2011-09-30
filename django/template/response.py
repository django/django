from django.http import HttpResponse
from django.template import loader, Context, RequestContext


class ContentNotRenderedError(Exception):
    pass


class SimpleTemplateResponse(HttpResponse):
    rendering_attrs = ['template_name', 'context_data', '_post_render_callbacks']

    def __init__(self, template, context=None, mimetype=None, status=None,
            content_type=None):
        # It would seem obvious to call these next two members 'template' and
        # 'context', but those names are reserved as part of the test Client
        # API. To avoid the name collision, we use tricky-to-debug problems
        self.template_name = template
        self.context_data = context

        self._post_render_callbacks = []

        # content argument doesn't make sense here because it will be replaced
        # with rendered template so we always pass empty string in order to
        # prevent errors and provide shorter signature.
        super(SimpleTemplateResponse, self).__init__('', mimetype, status,
                                                     content_type)

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
            return loader.select_template(template)
        elif isinstance(template, basestring):
            return loader.get_template(template)
        else:
            return template

    def resolve_context(self, context):
        """Converts context data into a full Context object
        (assuming it isn't already a Context object).
        """
        if isinstance(context, Context):
            return context
        else:
            return Context(context)

    @property
    def rendered_content(self):
        """Returns the freshly rendered content for the template and context
        described by the TemplateResponse.

        This *does not* set the final content of the response. To set the
        response content, you must either call render(), or set the
        content explicitly using the value of this property.
        """
        template = self.resolve_template(self.template_name)
        context = self.resolve_context(self.context_data)
        content = template.render(context)
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
            self._set_content(self.rendered_content)
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

    def _get_content(self):
        if not self._is_rendered:
            raise ContentNotRenderedError('The response content must be '
                                          'rendered before it can be accessed.')
        return super(SimpleTemplateResponse, self)._get_content()

    def _set_content(self, value):
        """Sets the content for the response
        """
        super(SimpleTemplateResponse, self)._set_content(value)
        self._is_rendered = True

    content = property(_get_content, _set_content)


class TemplateResponse(SimpleTemplateResponse):
    rendering_attrs = SimpleTemplateResponse.rendering_attrs + \
        ['_request', '_current_app']

    def __init__(self, request, template, context=None, mimetype=None,
            status=None, content_type=None, current_app=None):
        # self.request gets over-written by django.test.client.Client - and
        # unlike context_data and template_name the _request should not
        # be considered part of the public API.
        self._request = request
        # As a convenience we'll allow callers to provide current_app without
        # having to avoid needing to create the RequestContext directly
        self._current_app = current_app
        super(TemplateResponse, self).__init__(
            template, context, mimetype, status, content_type)

    def resolve_context(self, context):
        """Convert context data into a full RequestContext object
        (assuming it isn't already a Context object).
        """
        if isinstance(context, Context):
            return context
        return RequestContext(self._request, context, current_app=self._current_app)
