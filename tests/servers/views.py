from urllib.request import urlopen

from django.http import HttpResponse, StreamingHttpResponse
from django.views.decorators.csrf import csrf_exempt

from .models import Person


def example_view(request):
    return HttpResponse("example view")


def streaming_example_view(request):
    return StreamingHttpResponse((b"I", b"am", b"a", b"stream"))


def model_view(request):
    people = Person.objects.all()
    return HttpResponse("\n".join(person.name for person in people))


def create_model_instance(request):
    person = Person(name="emily")
    person.save()
    return HttpResponse()


def environ_view(request):
    return HttpResponse(
        "\n".join("%s: %r" % (k, v) for k, v in request.environ.items())
    )


def subview(request):
    return HttpResponse("subview")


def subview_calling_view(request):
    with urlopen(request.GET["url"] + "/subview/") as response:
        return HttpResponse("subview calling view: {}".format(response.read().decode()))


def check_model_instance_from_subview(request):
    with urlopen(request.GET["url"] + "/create_model_instance/"):
        pass
    with urlopen(request.GET["url"] + "/model_view/") as response:
        return HttpResponse("subview calling view: {}".format(response.read().decode()))


@csrf_exempt
def method_view(request):
    return HttpResponse(request.method)
