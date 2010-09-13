from django.http import HttpResponse

def empty_view(request, *args, **kwargs):
    return HttpResponse('')

def kwargs_view(request, arg1=1, arg2=2):
    return HttpResponse('')

def absolute_kwargs_view(request, arg1=1, arg2=2):
    return HttpResponse('')

class ViewClass(object):
    def __call__(self, request, *args, **kwargs):
        return HttpResponse('')

view_class_instance = ViewClass()

def bad_view(request, *args, **kwargs):
    raise ValueError("I don't think I'm getting good value for this view")
