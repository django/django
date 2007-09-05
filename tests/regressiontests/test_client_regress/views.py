from django.contrib.auth.decorators import login_required
from django.core.mail import EmailMessage, SMTPConnection
from django.http import HttpResponse, HttpResponseRedirect, HttpResponseServerError
from django.shortcuts import render_to_response

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
        return HttpResponse('')
    else:
        return HttpResponseServerError()

def get_view(request):
    "A simple login protected view"    
    return HttpResponse("Hello world")
get_view = login_required(get_view)

def login_protected_redirect_view(request):
    "A view that redirects all requests to the GET view"
    return HttpResponseRedirect('/test_client_regress/get_view/')
login_protected_redirect_view = login_required(login_protected_redirect_view)