from django.db import models


def set_attr(name, value):
    def wrapper(function):
        setattr(function, name, value)
        return function
    return wrapper


class Guitarist(models.Model):
    name = models.CharField(max_length=50)
    slug = models.CharField(max_length=50)

    @models.permalink
    def url(self):
        "Returns the URL for this guitarist."
        return ('guitarist_detail', [self.slug])

    @models.permalink
    @set_attr('attribute', 'value')
    def url_with_attribute(self):
        "Returns the URL for this guitarist and holds an attribute"
        return ('guitarist_detail', [self.slug])
