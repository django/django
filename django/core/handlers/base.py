import sys

from django import http
from django.core import signals
from django.dispatch import dispatcher

class BaseHandler(object):
    # Changes that are always applied to a response (in this order).
    response_fixes = [http.fix_location_header,
            http.conditional_content_removal]

    def __init__(self):
        self._request_middleware = self._view_middleware = self._response_middleware = self._exception_middleware = None

    def load_middleware(self):
        """
        Populate middleware lists from settings.MIDDLEWARE_CLASSES.

        Must be called after the environment is fixed (see __call__).
        """
        from django.conf import settings
        from django.core import exceptions
        self._request_middleware = []
        self._view_middleware = []
        self._response_middleware = []
        self._exception_middleware = []
        for middleware_path in settings.MIDDLEWARE_CLASSES:
            try:
                dot = middleware_path.rindex('.')
            except ValueError:
                raise exceptions.ImproperlyConfigured, '%s isn\'t a middleware module' % middleware_path
            mw_module, mw_classname = middleware_path[:dot], middleware_path[dot+1:]
            try:
                mod = __import__(mw_module, {}, {}, [''])
            except ImportError, e:
                raise exceptions.ImproperlyConfigured, 'Error importing middleware %s: "%s"' % (mw_module, e)
            try:
                mw_class = getattr(mod, mw_classname)
            except AttributeError:
                raise exceptions.ImproperlyConfigured, 'Middleware module "%s" does not define a "%s" class' % (mw_module, mw_classname)

            try:
                mw_instance = mw_class()
            except exceptions.MiddlewareNotUsed:
                continue

            if hasattr(mw_instance, 'process_request'):
                self._request_middleware.append(mw_instance.process_request)
            if hasattr(mw_instance, 'process_view'):
                self._view_middleware.append(mw_instance.process_view)
            if hasattr(mw_instance, 'process_response'):
                self._response_middleware.insert(0, mw_instance.process_response)
            if hasattr(mw_instance, 'process_exception'):
                self._exception_middleware.insert(0, mw_instance.process_exception)

    def get_response(self, request):
        "Returns an HttpResponse object for the given HttpRequest"
        from django.core import exceptions, urlresolvers
        from django.core.mail import mail_admins
        from django.conf import settings

        # Apply request middleware
        for middleware_method in self._request_middleware:
            response = middleware_method(request)
            if response:
                return response

        # Get urlconf from request object, if available.  Otherwise use default.
        urlconf = getattr(request, "urlconf", settings.ROOT_URLCONF)

        resolver = urlresolvers.RegexURLResolver(r'^/', urlconf)
        try:
            callback, callback_args, callback_kwargs = resolver.resolve(request.path)

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
                raise ValueError, "The view %s.%s didn't return an HttpResponse object." % (callback.__module__, view_name)

            return response
        except http.Http404, e:
            if settings.DEBUG:
                from django.views import debug
                return debug.technical_404_response(request, e)
            else:
                callback, param_dict = resolver.resolve404()
                return callback(request, **param_dict)
        except exceptions.PermissionDenied:
            return http.HttpResponseForbidden('<h1>Permission denied</h1>')
        except SystemExit:
            # Allow sys.exit() to actually exit. See tickets #1023 and #4701
            raise
        except: # Handle everything else, including SuspiciousOperation, etc.
            # Get the exception info now, in case another exception is thrown later.
            exc_info = sys.exc_info()
            receivers = dispatcher.send(signal=signals.got_request_exception, request=request)

            if settings.DEBUG_PROPAGATE_EXCEPTIONS:
                raise
            elif settings.DEBUG:
                from django.views import debug
                return debug.technical_500_response(request, *exc_info)
            else:
                # When DEBUG is False, send an error message to the admins.
                subject = 'Error (%s IP): %s' % ((request.META.get('REMOTE_ADDR') in settings.INTERNAL_IPS and 'internal' or 'EXTERNAL'), request.path)
                try:
                    request_repr = repr(request)
                except:
                    request_repr = "Request repr() unavailable"
                message = "%s\n\n%s" % (self._get_traceback(exc_info), request_repr)
                mail_admins(subject, message, fail_silently=True)
                # Return an HttpResponse that displays a friendly error message.
                callback, param_dict = resolver.resolve500()
                return callback(request, **param_dict)

    def _get_traceback(self, exc_info=None):
        "Helper function to return the traceback as a string"
        import traceback
        return '\n'.join(traceback.format_exception(*(exc_info or sys.exc_info())))

    def apply_response_fixes(self, request, response):
        """
        Applies each of the functions in self.response_fixes to the request and
        response, modifying the response in the process. Returns the new
        response.
        """
        for func in self.response_fixes:
            response = func(request, response)
        return response

