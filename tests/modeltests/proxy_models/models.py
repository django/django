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

class User(models.Model):
    name = models.CharField(max_length=100)

    def __unicode__(self):
        return self.name

class UserProxy(User):
    class Meta:
        proxy = True

class UserProxyProxy(UserProxy):
    class Meta:
        proxy = True

# We can still use `select_related()` to include related models in our querysets.
class Country(models.Model):
	name = models.CharField(max_length=50)

class State(models.Model):
	name = models.CharField(max_length=50)
	country = models.ForeignKey(Country)

	def __unicode__(self):
		return self.name

class StateProxy(State):
	class Meta:
		proxy = True

# Proxy models still works with filters (on related fields)
# and select_related, even when mixed with model inheritance
class BaseUser(models.Model):
    name = models.CharField(max_length=255)

class TrackerUser(BaseUser):
    status = models.CharField(max_length=50)

class ProxyTrackerUser(TrackerUser):
    class Meta:
        proxy = True


class Issue(models.Model):
    summary = models.CharField(max_length=255)
    assignee = models.ForeignKey(TrackerUser)

    def __unicode__(self):
        return ':'.join((self.__class__.__name__,self.summary,))

class Bug(Issue):
    version = models.CharField(max_length=50)
    reporter = models.ForeignKey(BaseUser)

class ProxyBug(Bug):
    """
    Proxy of an inherited class
    """
    class Meta:
        proxy = True


class ProxyProxyBug(ProxyBug):
    """
    A proxy of proxy model with related field
    """
    class Meta:
        proxy = True

class Improvement(Issue):
    """
    A model that has relation to a proxy model
    or to a proxy of proxy model
    """
    version = models.CharField(max_length=50)
    reporter = models.ForeignKey(ProxyTrackerUser)
    associated_bug = models.ForeignKey(ProxyProxyBug)

class ProxyImprovement(Improvement):
    class Meta:
        proxy = True

__test__ = {'API_TESTS' : """
# The MyPerson model should be generating the same database queries as the
# Person model (when the same manager is used in each case).
>>> from django.db import DEFAULT_DB_ALIAS
>>> MyPerson.other.all().query.get_compiler(DEFAULT_DB_ALIAS).as_sql() == Person.objects.order_by("name").query.get_compiler(DEFAULT_DB_ALIAS).as_sql()
True

# The StatusPerson models should have its own table (it's using ORM-level
# inheritance).
>>> StatusPerson.objects.all().query.get_compiler(DEFAULT_DB_ALIAS).as_sql() == Person.objects.all().query.get_compiler(DEFAULT_DB_ALIAS).as_sql()
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

# Correct type when querying a proxy of proxy

>>> MyPersonProxy.objects.all()
[<MyPersonProxy: Bazza del Frob>, <MyPersonProxy: Foo McBar>, <MyPersonProxy: homer>]

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

# Test save signals for proxy models
>>> from django.db.models import signals
>>> def make_handler(model, event):
...     def _handler(*args, **kwargs):
...         print u"%s %s save" % (model, event)
...     return _handler
>>> h1 = make_handler('MyPerson', 'pre')
>>> h2 = make_handler('MyPerson', 'post')
>>> h3 = make_handler('Person', 'pre')
>>> h4 = make_handler('Person', 'post')
>>> signals.pre_save.connect(h1, sender=MyPerson)
>>> signals.post_save.connect(h2, sender=MyPerson)
>>> signals.pre_save.connect(h3, sender=Person)
>>> signals.post_save.connect(h4, sender=Person)
>>> dino = MyPerson.objects.create(name=u"dino")
MyPerson pre save
MyPerson post save

# Test save signals for proxy proxy models
>>> h5 = make_handler('MyPersonProxy', 'pre')
>>> h6 = make_handler('MyPersonProxy', 'post')
>>> signals.pre_save.connect(h5, sender=MyPersonProxy)
>>> signals.post_save.connect(h6, sender=MyPersonProxy)
>>> dino = MyPersonProxy.objects.create(name=u"pebbles")
MyPersonProxy pre save
MyPersonProxy post save

>>> signals.pre_save.disconnect(h1, sender=MyPerson)
>>> signals.post_save.disconnect(h2, sender=MyPerson)
>>> signals.pre_save.disconnect(h3, sender=Person)
>>> signals.post_save.disconnect(h4, sender=Person)
>>> signals.pre_save.disconnect(h5, sender=MyPersonProxy)
>>> signals.post_save.disconnect(h6, sender=MyPersonProxy)

# A proxy has the same content type as the model it is proxying for (at the
# storage level, it is meant to be essentially indistinguishable).
>>> ctype = ContentType.objects.get_for_model
>>> ctype(Person) is ctype(OtherPerson)
True

>>> MyPersonProxy.objects.all()
[<MyPersonProxy: barney>, <MyPersonProxy: dino>, <MyPersonProxy: fred>, <MyPersonProxy: pebbles>]

>>> u = User.objects.create(name='Bruce')
>>> User.objects.all()
[<User: Bruce>]
>>> UserProxy.objects.all()
[<UserProxy: Bruce>]
>>> UserProxyProxy.objects.all()
[<UserProxyProxy: Bruce>]

# Proxy objects can be deleted
>>> u2 = UserProxy.objects.create(name='George')
>>> UserProxy.objects.all()
[<UserProxy: Bruce>, <UserProxy: George>]
>>> u2.delete()
>>> UserProxy.objects.all()
[<UserProxy: Bruce>]


# We can still use `select_related()` to include related models in our querysets.
>>> country = Country.objects.create(name='Australia')
>>> state = State.objects.create(name='New South Wales', country=country)

>>> State.objects.select_related()
[<State: New South Wales>]
>>> StateProxy.objects.select_related()
[<StateProxy: New South Wales>]
>>> StateProxy.objects.get(name='New South Wales')
<StateProxy: New South Wales>
>>> StateProxy.objects.select_related().get(name='New South Wales')
<StateProxy: New South Wales>

>>> contributor = TrackerUser.objects.create(name='Contributor',status='contrib')
>>> someone = BaseUser.objects.create(name='Someone')
>>> _ = Bug.objects.create(summary='fix this', version='1.1beta',
...                        assignee=contributor, reporter=someone)
>>> pcontributor = ProxyTrackerUser.objects.create(name='OtherContributor',
...                                                status='proxy')
>>> _ = Improvement.objects.create(summary='improve that', version='1.1beta',
...                                assignee=contributor, reporter=pcontributor,
...                                associated_bug=ProxyProxyBug.objects.all()[0])

# Related field filter on proxy
>>> ProxyBug.objects.get(version__icontains='beta')
<ProxyBug: ProxyBug:fix this>

# Select related + filter on proxy
>>> ProxyBug.objects.select_related().get(version__icontains='beta')
<ProxyBug: ProxyBug:fix this>

# Proxy of proxy, select_related + filter
>>> ProxyProxyBug.objects.select_related().get(version__icontains='beta')
<ProxyProxyBug: ProxyProxyBug:fix this>

# Select related + filter on a related proxy field
>>> ProxyImprovement.objects.select_related().get(reporter__name__icontains='butor')
<ProxyImprovement: ProxyImprovement:improve that>

# Select related + filter on a related proxy of proxy field
>>> ProxyImprovement.objects.select_related().get(associated_bug__summary__icontains='fix')
<ProxyImprovement: ProxyImprovement:improve that>

Proxy models can be loaded from fixtures (Regression for #11194)
>>> from django.core import management
>>> management.call_command('loaddata', 'mypeople.json', verbosity=0)
>>> MyPerson.objects.get(pk=100)
<MyPerson: Elvis Presley>

"""}
