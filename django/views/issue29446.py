from django.shortcuts import render
from django.http import HttpResponse
from django.template import loader

def index(request):
    template = loader.get_template('myfirst.html')
    x = "hello world"
    context = {
        'message':x
    }
    request.view_context = context
    return HttpResponse(template.render(context))

# Create your views here.
