from django.core.mail import EmailMessage, SMTPConnection
from django.http import HttpResponse, HttpResponseServerError
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

