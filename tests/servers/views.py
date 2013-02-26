from django.http import HttpResponse
from .models import Person


def example_view(request):
    return HttpResponse('example view')


def model_view(request):
    people = Person.objects.all()
    return HttpResponse('\n'.join([person.name for person in people]))


def create_model_instance(request):
    person = Person(name='emily')
    person.save()
    return HttpResponse('')


def environ_view(request):
    return HttpResponse("\n".join(["%s: %r" % (k, v) for k, v in request.environ.items()]))
