from django.core.mail import EmailMessage, SMTPConnection
from django.http import HttpResponse
from django.shortcuts import render_to_response

def no_template_view(request):
    "A simple view that expects a GET request, and returns a rendered template"
    return HttpResponse("No template used")

