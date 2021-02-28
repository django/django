from django.urls import path

from . import views

urlpatterns = [
    path('{x}/<{x}:{x}>/'.format(x=name), views.empty_view, name=name)
    for name in ('int', 'base36', 'path', 'slug', 'str', 'uuid')
]
