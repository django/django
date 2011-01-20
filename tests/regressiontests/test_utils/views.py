from django.http import HttpResponse
from django.shortcuts import get_object_or_404
from models import Person

def get_person(request, pk):
    person = get_object_or_404(Person, pk=pk)
    return HttpResponse(person.name)