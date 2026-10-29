from django.views.generic import ListView


def view_func_namespaced_unnamed(request):
    pass


def view_func_namespaced_named(request):
    pass


def view_func_nons_unnamed(request):
    pass


def view_func_nons_named(request):
    pass


class CBV(ListView):
    pass
