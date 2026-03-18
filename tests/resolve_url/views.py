from django.http import HttpResponse
from django.views import View


def some_view(request):
    return HttpResponse("ok")


def params_view(request, slug):
    return HttpResponse(f"Params: {slug}")


class SomeView(View):
    def get(self, request):
        return HttpResponse("ok")


class ParamsView(View):
    def get(self, request, pk):
        return HttpResponse(f"Params: {pk}")


some_cbv = SomeView.as_view()
params_cbv = ParamsView.as_view()
