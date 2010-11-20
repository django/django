from django import http
from django.core.exceptions import ImproperlyConfigured
from django.template import RequestContext, loader
from django.utils.functional import update_wrapper
from django.utils.log import getLogger
from django.utils.decorators import classonlymethod

logger = getLogger('django.request')

class View(object):
    """
    Intentionally simple parent class for all views. Only implements
    dispatch-by-method and simple sanity checking.
    """

    http_method_names = ['get', 'post', 'put', 'delete', 'head', 'options', 'trace']

    def __init__(self, **kwargs):
        """
        Constructor. Called in the URLconf; can contain helpful extra
        keyword arguments, and other things.
        """
        # Go through keyword arguments, and either save their values to our
        # instance, or raise an error.
        for key, value in kwargs.iteritems():
            setattr(self, key, value)

    @classonlymethod
    def as_view(cls, **initkwargs):
        """
        Main entry point for a request-response process.
        """
        # sanitize keyword arguments
        for key in initkwargs:
            if key in cls.http_method_names:
                raise TypeError(u"You tried to pass in the %s method name as a "
                                u"keyword argument to %s(). Don't do that."
                                % (key, cls.__name__))
            if not hasattr(cls, key):
                raise TypeError(u"%s() received an invalid keyword %r" % (
                    cls.__name__, key))

        def view(request, *args, **kwargs):
            self = cls(**initkwargs)
            return self.dispatch(request, *args, **kwargs)

        # take name and docstring from class
        update_wrapper(view, cls, updated=())

        # and possible attributes set by decorators
        # like csrf_exempt from dispatch
        update_wrapper(view, cls.dispatch, assigned=())
        return view

    def dispatch(self, request, *args, **kwargs):
        # Try to dispatch to the right method; if a method doesn't exist,
        # defer to the error handler. Also defer to the error handler if the
        # request method isn't on the approved list.
        if request.method.lower() in self.http_method_names:
            handler = getattr(self, request.method.lower(), self.http_method_not_allowed)
        else:
            handler = self.http_method_not_allowed
        self.request = request
        self.args = args
        self.kwargs = kwargs
        return handler(request, *args, **kwargs)

    def http_method_not_allowed(self, request, *args, **kwargs):
        allowed_methods = [m for m in self.http_method_names if hasattr(self, m)]
        logger.warning('Method Not Allowed (%s): %s' % (request.method, request.path),
            extra={
                'status_code': 405,
                'request': self.request
            }
        )
        return http.HttpResponseNotAllowed(allowed_methods)


class TemplateResponseMixin(object):
    """
    A mixin that can be used to render a template.
    """
    template_name = None

    def render_to_response(self, context):
        """
        Returns a response with a template rendered with the given context.
        """
        return self.get_response(self.render_template(context))

    def get_response(self, content, **httpresponse_kwargs):
        """
        Construct an `HttpResponse` object.
        """
        return http.HttpResponse(content, **httpresponse_kwargs)

    def render_template(self, context):
        """
        Render the template with a given context.
        """
        context_instance = self.get_context_instance(context)
        return self.get_template().render(context_instance)

    def get_context_instance(self, context):
        """
        Get the template context instance. Must return a Context (or subclass)
        instance.
        """
        return RequestContext(self.request, context)

    def get_template(self):
        """
        Get a ``Template`` object for the given request.
        """
        names = self.get_template_names()
        if not names:
            raise ImproperlyConfigured(u"'%s' must provide template_name."
                                       % self.__class__.__name__)
        return self.load_template(names)

    def get_template_names(self):
        """
        Return a list of template names to be used for the request. Must return
        a list. May not be called if get_template is overridden.
        """
        if self.template_name is None:
            return []
        else:
            return [self.template_name]

    def load_template(self, names):
        """
        Load a list of templates using the default template loader.
        """
        return loader.select_template(names)


class TemplateView(TemplateResponseMixin, View):
    """
    A view that renders a template.
    """
    def get_context_data(self, **kwargs):
        return {
            'params': kwargs
        }

    def get(self, request, *args, **kwargs):
        context = self.get_context_data(**kwargs)
        return self.render_to_response(context)


class RedirectView(View):
    """
    A view that provides a redirect on any GET request.
    """
    permanent = True
    url = None
    query_string = False

    def get_redirect_url(self, **kwargs):
        """
        Return the URL redirect to. Keyword arguments from the
        URL pattern match generating the redirect request
        are provided as kwargs to this method.
        """
        if self.url:
            args = self.request.META["QUERY_STRING"]
            if args and self.query_string:
                url = "%s?%s" % (self.url, args)
            else:
                url = self.url
            return url % kwargs
        else:
            return None

    def get(self, request, *args, **kwargs):
        url = self.get_redirect_url(**kwargs)
        if url:
            if self.permanent:
                return http.HttpResponsePermanentRedirect(url)
            else:
                return http.HttpResponseRedirect(url)
        else:
            logger.warning('Gone: %s' % self.request.path,
                        extra={
                            'status_code': 410,
                            'request': self.request
                        })
            return http.HttpResponseGone()
