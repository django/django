"""
By specifying the 'proxy' Meta attribute, model subclasses can specify that
they will take data directly from the table of their base class table rather
than using a new table of their own. This allows them to act as simple proxies,
providing a modified interface to the data from the base class.
"""

from django.contrib.contenttypes.models import ContentType
from django.db import models


# A couple of managers for testing managing overriding in proxy model cases.

class PersonManager(models.Manager):
    def get_query_set(self):
        return super(PersonManager, self).get_query_set().exclude(name="fred")

class SubManager(models.Manager):
    def get_query_set(self):
        return super(SubManager, self).get_query_set().exclude(name="wilma")

class Person(models.Model):
    """
    A simple concrete base class.
    """
    name = models.CharField(max_length=50)

    objects = PersonManager()

    def __unicode__(self):
        return self.name

class Abstract(models.Model):
    """
    A simple abstract base class, to be used for error checking.
    """
    data = models.CharField(max_length=10)

    class Meta:
        abstract = True

class MyPerson(Person):
    """
    A proxy subclass, this should not get a new table. Overrides the default
    manager.
    """
    class Meta:
        proxy = True
        ordering = ["name"]

    objects = SubManager()
    other = PersonManager()

    def has_special_name(self):
        return self.name.lower() == "special"

class ManagerMixin(models.Model):
    excluder = SubManager()

    class Meta:
        abstract = True

class OtherPerson(Person, ManagerMixin):
    """
    A class with the default manager from Person, plus an secondary manager.
    """
    class Meta:
        proxy = True
        ordering = ["name"]

class StatusPerson(MyPerson):
    """
    A non-proxy subclass of a proxy, it should get a new table.
    """
    status = models.CharField(max_length=80)

# We can even have proxies of proxies (and subclass of those).
class MyPersonProxy(MyPerson):
    class Meta:
        proxy = True

class LowerStatusPerson(MyPersonProxy):
    status = models.CharField(max_length=80)

__test__ = {'API_TESTS' : """
# The MyPerson model should be generating the same database queries as the
# Person model (when the same manager is used in each case).
>>> MyPerson.other.all().query.as_sql() == Person.objects.order_by("name").query.as_sql()
True

# The StatusPerson models should have its own table (it's using ORM-level
# inheritance).
>>> StatusPerson.objects.all().query.as_sql() == Person.objects.all().query.as_sql()
False

# Creating a Person makes them accessible through the MyPerson proxy.
>>> _ = Person.objects.create(name="Foo McBar")
>>> len(Person.objects.all())
1
>>> len(MyPerson.objects.all())
1
>>> MyPerson.objects.get(name="Foo McBar").id
1
>>> MyPerson.objects.get(id=1).has_special_name()
False

# Person is not proxied by StatusPerson subclass, however.
>>> StatusPerson.objects.all()
[]

# A new MyPerson also shows up as a standard Person
>>> _ = MyPerson.objects.create(name="Bazza del Frob")
>>> len(MyPerson.objects.all())
2
>>> len(Person.objects.all())
2

>>> _ = LowerStatusPerson.objects.create(status="low", name="homer")
>>> LowerStatusPerson.objects.all()
[<LowerStatusPerson: homer>]

# And now for some things that shouldn't work...
#
# All base classes must be non-abstract
>>> class NoAbstract(Abstract):
...     class Meta:
...         proxy = True
Traceback (most recent call last):
    ....
TypeError: Abstract base class containing model fields not permitted for proxy model 'NoAbstract'.

# The proxy must actually have one concrete base class
>>> class TooManyBases(Person, Abstract):
...     class Meta:
...         proxy = True
Traceback (most recent call last):
    ....
TypeError: Abstract base class containing model fields not permitted for proxy model 'TooManyBases'.

>>> class NoBaseClasses(models.Model):
...     class Meta:
...         proxy = True
Traceback (most recent call last):
    ....
TypeError: Proxy model 'NoBaseClasses' has no non-abstract model base class.


# A proxy cannot introduce any new fields
>>> class NoNewFields(Person):
...     newfield = models.BooleanField()
...     class Meta:
...         proxy = True
Traceback (most recent call last):
    ....
FieldError: Proxy model 'NoNewFields' contains model fields.

# Manager tests.

>>> Person.objects.all().delete()
>>> _ = Person.objects.create(name="fred")
>>> _ = Person.objects.create(name="wilma")
>>> _ = Person.objects.create(name="barney")

>>> MyPerson.objects.all()
[<MyPerson: barney>, <MyPerson: fred>]
>>> MyPerson._default_manager.all()
[<MyPerson: barney>, <MyPerson: fred>]

>>> OtherPerson.objects.all()
[<OtherPerson: barney>, <OtherPerson: wilma>]
>>> OtherPerson.excluder.all()
[<OtherPerson: barney>, <OtherPerson: fred>]
>>> OtherPerson._default_manager.all()
[<OtherPerson: barney>, <OtherPerson: wilma>]

# A proxy has the same content type as the model it is proxying for (at the
# storage level, it is meant to be essentially indistinguishable).
>>> ctype = ContentType.objects.get_for_model
>>> ctype(Person) is ctype(OtherPerson)
True
"""}


