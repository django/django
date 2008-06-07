import os

from django.contrib.auth.decorators import login_required
from django.http import HttpResponse, HttpResponseRedirect, HttpResponseServerError
from django.core.exceptions import SuspiciousOperation

def no_template_view(request):
    "A simple view that expects a GET request, and returns a rendered template"
    return HttpResponse("No template used. Sample content: twice once twice. Content ends.")

def file_upload_view(request):
    """
    Check that a file upload can be updated into the POST dictionary without
    going pear-shaped.
    """
    form_data = request.POST.copy()
    form_data.update(request.FILES)
    if isinstance(form_data['file_field'], dict) and isinstance(form_data['name'], unicode):
        # If a file is posted, the dummy client should only post the file name,
        # not the full path.
        if os.path.dirname(form_data['file_field']['filename']) != '':
            return HttpResponseServerError()            
        return HttpResponse('')
    else:
        return HttpResponseServerError()

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