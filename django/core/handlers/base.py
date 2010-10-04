import logging
import sys

from django import http
from django.core import signals
from django.utils.encoding import force_unicode
from django.utils.importlib import import_module

logger = logging.getLogger('django.request')


class BaseHandler(object):
    # Changes that are always applied to a response (in this order).
    response_fixes = [
        http.fix_location_header,
        http.conditional_content_removal,
        http.fix_IE_for_attach,
        http.fix_IE_for_vary,
    ]

    def __init__(self):
        self._request_middleware = self._view_middleware = self._response_middleware = self._exception_middleware = None

    def load_middleware(self):
        """
        Populate middleware lists from settings.MIDDLEWARE_CLASSES.

        Must be called after the environment is fixed (see __call__).
        """
        from django.conf import settings
        from django.core import exceptions
        self._view_middleware = []
        self._response_middleware = []
        self._exception_middleware = []

        request_middleware = []
        for middleware_path in settings.MIDDLEWARE_CLASSES:
            try:
                dot = middleware_path.rindex('.')
            except ValueError:
                raise exceptions.ImproperlyConfigured('%s isn\'t a middleware module' % middleware_path)
            mw_module, mw_classname = middleware_path[:dot], middleware_path[dot+1:]
            try:
                mod = import_module(mw_module)
            except ImportError, e:
                raise exceptions.ImproperlyConfigured('Error importing middleware %s: "%s"' % (mw_module, e))
            try:
                mw_class = getattr(mod, mw_classname)
            except AttributeError:
                raise exceptions.ImproperlyConfigured('Middleware module "%s" does not define a "%s" class' % (mw_module, mw_classname))

            try:
                mw_instance = mw_class()
            except exceptions.MiddlewareNotUsed:
                continue

            if hasattr(mw_instance, 'process_request'):
                request_middleware.append(mw_instance.process_request)
            if hasattr(mw_instance, 'process_view'):
                self._view_middleware.append(mw_instance.process_view)
            if hasattr(mw_instance, 'process_response'):
                self._response_middleware.insert(0, mw_instance.process_response)
            if hasattr(mw_instance, 'process_exception'):
                self._exception_middleware.insert(0, mw_instance.process_exception)

        # We only assign to this when initialization is complete as it is used
        # as a flag for initialization being complete.
        self._request_middleware = request_middleware

    def get_response(self, request):
        "Returns an HttpResponse object for the given HttpRequest"
        from django.core import exceptions, urlresolvers
        from django.conf import settings

        try:
            try:
                # Setup default url resolver for this thread.
                urlconf = settings.ROOT_URLCONF
                urlresolvers.set_urlconf(urlconf)
                resolver = urlresolvers.RegexURLResolver(r'^/', urlconf)

                # Apply request middleware
                for middleware_method in self._request_middleware:
                    response = middleware_method(request)
                    if response:
                        return response

                if hasattr(request, "urlconf"):
                    # Reset url resolver with a custom urlconf.
                    urlconf = request.urlconf
                    urlresolvers.set_urlconf(urlconf)
                    resolver = urlresolvers.RegexURLResolver(r'^/', urlconf)

                callback, callback_args, callback_kwargs = resolver.resolve(
                        request.path_info)

                # Apply view middleware
                for middleware_method in self._view_middleware:
                    response = middleware_method(request, callback, callback_args, callback_kwargs)
                    if response:
                        return response

                try:
                    response = callback(request, *callback_args, **callback_kwargs)
                except Exception, e:
                    # If the view raised an exception, run it through exception
                    # middleware, and if the exception middleware returns a
                    # response, use that. Otherwise, reraise the exception.
                    for middleware_method in self._exception_middleware:
                        response = middleware_method(request, e)
                        if response:
                            return response
                    raise

                # Complain if the view returned None (a common error).
                if response is None:
                    try:
                        view_name = callback.func_name # If it's a function
                    except AttributeError:
                        view_name = callback.__class__.__name__ + '.__call__' # If it's a class
                    raise ValueError("The view %s.%s didn't return an HttpResponse object." % (callback.__module__, view_name))

                return response
            except http.Http404, e:
                logger.warning('Not Found: %s' % request.path,
                            extra={
                                'status_code': 404,
                                'request': request
                            })
                if settings.DEBUG:
                    from django.views import debug
                    return debug.technical_404_response(request, e)
                else:
                    try:
                        callback, param_dict = resolver.resolve404()
                        return callback(request, **param_dict)
                    except:
                        try:
                            return self.handle_uncaught_exception(request, resolver, sys.exc_info())
                        finally:
                            receivers = signals.got_request_exception.send(sender=self.__class__, request=request)
            except exceptions.PermissionDenied:
                logger.warning('Forbidden (Permission denied): %s' % request.path,
                            extra={
                                'status_code': 403,
                                'request': request
                            })
                return http.HttpResponseForbidden('<h1>Permission denied</h1>')
            except SystemExit:
                # Allow sys.exit() to actually exit. See tickets #1023 and #4701
                raise
            except: # Handle everything else, including SuspiciousOperation, etc.
                # Get the exception info now, in case another exception is thrown later.
                receivers = signals.got_request_exception.send(sender=self.__class__, request=request)
                return self.handle_uncaught_exception(request, resolver, sys.exc_info())
        finally:
            # Reset URLconf for this thread on the way out for complete
            # isolation of request.urlconf
            urlresolvers.set_urlconf(None)

    def handle_uncaught_exception(self, request, resolver, exc_info):
        """
        Processing for any otherwise uncaught exceptions (those that will
        generate HTTP 500 responses). Can be overridden by subclasses who want
        customised 500 handling.

        Be *very* careful when overriding this because the error could be
        caused by anything, so assuming something like the database is always
        available would be an error.
        """
        from django.conf import settings

        if settings.DEBUG_PROPAGATE_EXCEPTIONS:
            raise

        if settings.DEBUG:
            from django.views import debug
            return debug.technical_500_response(request, *exc_info)

        logger.error('Internal Server Error: %s' % request.path,
            exc_info=exc_info,
            extra={
                'status_code': 500,
                'request':request
            }
        )

        # If Http500 handler is not installed, re-raise last exception
        if resolver.urlconf_module is None:
            raise exc_info[1], None, exc_info[2]
        # Return an HttpResponse that displays a friendly error message.
        callback, param_dict = resolver.resolve500()
        return callback(request, **param_dict)

    def apply_response_fixes(self, request, response):
        """
        Applies each of the functions in self.response_fixes to the request and
        response, modifying the response in the process. Returns the new
        response.
        """
        for func in self.response_fixes:
            response = func(request, response)
        return response

def get_script_name(environ):
    """
    Returns the equivalent of the HTTP request's SCRIPT_NAME environment
    variable. If Apache mod_rewrite has been used, returns what would have been
    the script name prior to any rewriting (so it's the script name as seen
    from the client's perspective), unless DJANGO_USE_POST_REWRITE is set (to
    anything).
    """
    from django.conf import settings
    if settings.FORCE_SCRIPT_NAME is not None:
        return force_unicode(settings.FORCE_SCRIPT_NAME)

    # If Apache's mod_rewrite had a whack at the URL, Apache set either
    # SCRIPT_URL or REDIRECT_URL to the full resource URL before applying any
    # rewrites. Unfortunately not every webserver (lighttpd!) passes this
    # information through all the time, so FORCE_SCRIPT_NAME, above, is still
    # needed.
    script_url = environ.get('SCRIPT_URL', u'')
    if not script_url:
        script_url = environ.get('REDIRECT_URL', u'')
    if script_url:
        return force_unicode(script_url[:-len(environ.get('PATH_INFO', ''))])
    return force_unicode(environ.get('SCRIPT_NAME', u''))

