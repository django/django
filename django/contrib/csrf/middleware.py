"""
Cross Site Request Forgery Middleware.

This module provides a middleware that implements protection
against request forgeries from other sites. 

"""
from django.conf import settings
from django.http import HttpResponseForbidden
import md5
import re

_ERROR_MSG = "<h1>403 Forbidden</h1><p>Cross Site Request Forgery detected.  Request aborted.</p>"

_POST_FORM_RE = \
    re.compile(r'(<form\W[^>]*\bmethod=(\'|"|)POST(\'|"|)\b[^>]*>)', re.IGNORECASE)
    
_HTML_TYPES = ('text/html', 'application/xhtml+xml')    

def _make_token(session_id):
    return md5.new(settings.SECRET_KEY + session_id).hexdigest()
    
class CsrfMiddleware(object):
    """Django middleware that adds protection against Cross Site
    Request Forgeries by adding hidden form fields to POST forms and 
    checking requests for the correct value.  
    
    In the list of middlewares, SessionMiddleware is required, and must come 
    after this middleware.  CsrfMiddleWare must come after compression 
    middleware.
   
    If a session ID cookie is present, it is hashed with the SECRET_KEY 
    setting to create an authentication token.  This token is added to all 
    outgoing POST forms and is expected on all incoming POST requests that 
    have a session ID cookie.
    
    If you are setting cookies directly, instead of using Django's session 
    framework, this middleware will not work.
    """
    
    def process_request(self, request):
        if request.POST:
            try:
                session_id = request.COOKIES[settings.SESSION_COOKIE_NAME]
            except KeyError:
                # No session, no check required
                return None

            csrf_token = _make_token(session_id)
            # check incoming token
            try:
                request_csrf_token = request.POST['csrfmiddlewaretoken']
            except KeyError:
                return HttpResponseForbidden(_ERROR_MSG)
            
            if request_csrf_token != csrf_token:
                return HttpResponseForbidden(_ERROR_MSG)
                
        return None
        
    def process_response(self, request, response):
        csrf_token = None
        try:
            cookie = response.cookies[settings.SESSION_COOKIE_NAME]
            csrf_token = _make_token(cookie.value)
        except KeyError:
            # No outgoing cookie to set session, but 
            # a session might already exist.
            try:
                session_id = request.COOKIES[settings.SESSION_COOKIE_NAME]
                csrf_token = _make_token(session_id)
            except KeyError:
                # no incoming or outgoing cookie
                pass
            
        if csrf_token is not None and \
           response['Content-Type'].split(';')[0] in _HTML_TYPES:
           
            # Modify any POST forms
            extra_field = "<div style='display:none;'>" + \
                "<input type='hidden' name='csrfmiddlewaretoken' value='" + \
                csrf_token + "' /></div>"
            response.content = _POST_FORM_RE.sub('\\1' + extra_field, response.content)
        return response
