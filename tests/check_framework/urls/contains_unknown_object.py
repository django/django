from django.conf.urls import include, url

class Foo:
    pass

obj = Foo()
obj.regex = ''

urlpatterns = [
    url('^', include([
        obj,
    ])),
]
