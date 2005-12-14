"""
23. Giving models a custom manager
"""

from django.db import models

# An example of providing a custom manager called "objects".

class PersonManager(models.Manager):
    def get_fun_people(self):
        return self.get_list(fun__exact=True)

class Person(models.Model):
    first_name = models.CharField(maxlength=30)
    last_name = models.CharField(maxlength=30)
    fun = models.BooleanField()
    objects = PersonManager()

    def __repr__(self):
        return "%s %s" % (self.first_name, self.last_name)

# An example of providing a custom manager that isn't called "objects".

class PublishedBookManager(models.Manager):
    def get_list(self, **kwargs):
        kwargs['is_published__exact'] = True
        return models.Manager.get_list(self, **kwargs)

class Book(models.Model):
    title = models.CharField(maxlength=50)
    author = models.CharField(maxlength=30)
    is_published = models.BooleanField()
    published_objects = PublishedBookManager()

    def __repr__(self):
        return self.title

# An example of providing multiple custom managers.

class FastCarManager(models.Manager):
    def get_list(self, **kwargs):
        kwargs['top_speed__gt'] = 150
        return models.Manager.get_list(self, **kwargs)

class Car(models.Model):
    name = models.CharField(maxlength=10)
    mileage = models.IntegerField()
    top_speed = models.IntegerField(help_text="In miles per hour.")
    cars = models.Manager()
    fast_cars = FastCarManager()

    def __repr__(self):
        return self.name

API_TESTS = """
>>> p1 = Person(first_name='Bugs', last_name='Bunny', fun=True)
>>> p1.save()
>>> p2 = Person(first_name='Droopy', last_name='Dog', fun=False)
>>> p2.save()
>>> Person.objects.get_fun_people()
[Bugs Bunny]

>>> b1 = Book(title='How to program', author='Rodney Dangerfield', is_published=True)
>>> b1.save()
>>> b2 = Book(title='How to be smart', author='Albert Einstein', is_published=False)
>>> b2.save()

# The default manager, "objects", doesn't exist,
# because a custom one was provided.
>>> Book.objects
Traceback (most recent call last):
    ...
AttributeError: type object 'Book' has no attribute 'objects'

>>> Book.published_objects.get_list()
[How to program]

>>> c1 = Car(name='Corvette', mileage=21, top_speed=180)
>>> c1.save()
>>> c2 = Car(name='Neon', mileage=31, top_speed=100)
>>> c2.save()
>>> Car.cars.get_list(order_by=('name',))
[Corvette, Neon]
>>> Car.fast_cars.get_list()
[Corvette]

# Each model class gets a "_default_manager" attribute, which is a reference
# to the first manager defined in the class. In this case, it's "cars".
>>> Car._default_manager.get_list(order_by=('name',))
[Corvette, Neon]
"""
