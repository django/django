"""
40. Tests for select_related()

``select_related()`` follows all relationships and pre-caches any foreign key
values so that complex trees can be fetched in a single query. However, this
isn't always a good idea, so the ``depth`` argument control how many "levels"
the select-related behavior will traverse.
"""

from django.db import models

# Who remembers high school biology?

class Domain(models.Model):
    name = models.CharField(maxlength=50)
    def __str__(self):
        return self.name

class Kingdom(models.Model):
    name = models.CharField(maxlength=50)
    domain = models.ForeignKey(Domain)
    def __str__(self):
        return self.name

class Phylum(models.Model):
    name = models.CharField(maxlength=50)
    kingdom = models.ForeignKey(Kingdom)
    def __str__(self):
        return self.name
    
class Klass(models.Model):
    name = models.CharField(maxlength=50)
    phylum = models.ForeignKey(Phylum)
    def __str__(self):
        return self.name
    
class Order(models.Model):
    name = models.CharField(maxlength=50)
    klass = models.ForeignKey(Klass)
    def __str__(self):
        return self.name

class Family(models.Model):
    name = models.CharField(maxlength=50)
    order = models.ForeignKey(Order)
    def __str__(self):
        return self.name

class Genus(models.Model):
    name = models.CharField(maxlength=50)
    family = models.ForeignKey(Family)
    def __str__(self):
        return self.name

class Species(models.Model):
    name = models.CharField(maxlength=50)
    genus = models.ForeignKey(Genus)
    def __str__(self):
        return self.name

def create_tree(stringtree):
    """Helper to create a complete tree"""
    names = stringtree.split()
    models = [Domain, Kingdom, Phylum, Klass, Order, Family, Genus, Species]
    assert len(names) == len(models), (names, models)
    
    parent = None
    for name, model in zip(names, models):
        try:
            obj = model.objects.get(name=name)
        except model.DoesNotExist:
            obj = model(name=name)
        if parent:
            setattr(obj, parent.__class__.__name__.lower(), parent)
        obj.save()
        parent = obj

__test__ = {'API_TESTS':"""

# Set up.
# The test runner sets settings.DEBUG to False, but we want to gather queries
# so we'll set it to True here and reset it at the end of the test suite.
>>> from django.conf import settings
>>> settings.DEBUG = True

>>> create_tree("Eukaryota Animalia Anthropoda Insecta Diptera Drosophilidae Drosophila melanogaster")
>>> create_tree("Eukaryota Animalia Chordata Mammalia Primates Hominidae Homo sapiens")
>>> create_tree("Eukaryota Plantae Magnoliophyta Magnoliopsida Fabales Fabaceae Pisum sativum")
>>> create_tree("Eukaryota Fungi Basidiomycota Homobasidiomycatae Agaricales Amanitacae Amanita muscaria")

>>> from django import db

# Normally, accessing FKs doesn't fill in related objects:
>>> db.reset_queries()
>>> fly = Species.objects.get(name="melanogaster")
>>> fly.genus.family.order.klass.phylum.kingdom.domain
<Domain: Eukaryota>
>>> len(db.connection.queries)
8

# However, a select_related() call will fill in those related objects without any extra queries:
>>> db.reset_queries()
>>> person = Species.objects.select_related().get(name="sapiens")
>>> person.genus.family.order.klass.phylum.kingdom.domain
<Domain: Eukaryota>
>>> len(db.connection.queries)
1

# select_related() also of course applies to entire lists, not just items.
# Without select_related()
>>> db.reset_queries()
>>> world = Species.objects.all()
>>> [o.genus.family for o in world]
[<Family: Drosophilidae>, <Family: Hominidae>, <Family: Fabaceae>, <Family: Amanitacae>]
>>> len(db.connection.queries)
9

# With select_related():
>>> db.reset_queries()
>>> world = Species.objects.all().select_related()
>>> [o.genus.family for o in world]
[<Family: Drosophilidae>, <Family: Hominidae>, <Family: Fabaceae>, <Family: Amanitacae>]
>>> len(db.connection.queries)
1

# The "depth" argument to select_related() will stop the descent at a particular level:
>>> db.reset_queries()
>>> pea = Species.objects.select_related(depth=1).get(name="sativum")
>>> pea.genus.family.order.klass.phylum.kingdom.domain
<Domain: Eukaryota>

# Notice: one few query than above because of depth=1
>>> len(db.connection.queries)
7

>>> db.reset_queries()
>>> pea = Species.objects.select_related(depth=5).get(name="sativum")
>>> pea.genus.family.order.klass.phylum.kingdom.domain
<Domain: Eukaryota>
>>> len(db.connection.queries)
3

>>> db.reset_queries()
>>> world = Species.objects.all().select_related(depth=2)
>>> [o.genus.family.order for o in world]
[<Order: Diptera>, <Order: Primates>, <Order: Fabales>, <Order: Agaricales>]
>>> len(db.connection.queries)
5

# Reset DEBUG to where we found it.
>>> settings.DEBUG = False
"""}
