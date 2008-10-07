from django.contrib.auth.decorators import login_required
from django.http import HttpResponse, HttpResponseRedirect
from django.core.exceptions import SuspiciousOperation

def no_template_view(request):
    "A simple view that expects a GET request, and returns a rendered template"
    return HttpResponse("No template used. Sample content: twice once twice. Content ends.")

def staff_only_view(request):
    "A view that can only be visited by staff. Non staff members get an exception"
    if request.user.is_staff:
        return HttpResponse('')
    else:
        raise SuspiciousOperation()

def get_view(request):
    "A simple login protected view"
    return HttpResponse("Hello world")
get_view = login_required(get_view)

def view_with_argument(request, name):
    """A view that takes a string argument

    The purpose of this view is to check that if a space is provided in
    the argument, the test framework unescapes the %20 before passing
    the value to the view.
    """
    if name == 'Arthur Dent':
        return HttpResponse('Hi, Arthur')
    else:
        return HttpResponse('Howdy, %s' % name)

def login_protected_redirect_view(request):
    "A view that redirects all requests to the GET view"
    return HttpResponseRedirect('/test_client_regress/get_view/')
login_protected_redirect_view = login_required(login_protected_redirect_view)

def set_session_view(request):
    "A view that sets a session variable"
    request.session['session_var'] = 'YES'
    return HttpResponse('set_session')

def check_session_view(request):
    "A view that reads a session variable"
    return HttpResponse(request.session.get('session_var', 'NO'))

def request_methods_view(request):
    "A view that responds with the request method"
    return HttpResponse('request method: %s' % request.method)