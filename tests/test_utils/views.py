from freedom.http import HttpResponse
from freedom.shortcuts import get_object_or_404
from freedom.template import loader, Context

from .models import Person


def get_person(request, pk):
    person = get_object_or_404(Person, pk=pk)
    return HttpResponse(person.name)


def no_template_used(request):
    template = loader.get_template_from_string("This is a string-based template")
    return HttpResponse(template.render(Context({})))


def empty_response(request):
    return HttpResponse('')
