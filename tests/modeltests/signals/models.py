"""
Testing signals before/after saving and deleting.
"""

from django.db import models
from django.dispatch import receiver

class Person(models.Model):
    first_name = models.CharField(max_length=20)
    last_name = models.CharField(max_length=20)

    def __unicode__(self):
        return u"%s %s" % (self.first_name, self.last_name)

class Car(models.Model):
    make = models.CharField(max_length=20)
    model = models.CharField(max_length=20)

    def __unicode__(self):
        return u"%s %s" % (self.make, self.model)

def pre_save_test(signal, sender, instance, **kwargs):
    print 'pre_save signal,', instance
    if kwargs.get('raw'):
        print 'Is raw'

def post_save_test(signal, sender, instance, **kwargs):
    print 'post_save signal,', instance
    if 'created' in kwargs:
        if kwargs['created']:
            print 'Is created'
        else:
            print 'Is updated'
    if kwargs.get('raw'):
        print 'Is raw'

def pre_delete_test(signal, sender, instance, **kwargs):
    print 'pre_delete signal,', instance
    print 'instance.id is not None: %s' % (instance.id != None)

# #8285: signals can be any callable
class PostDeleteHandler(object):
    def __call__(self, signal, sender, instance, **kwargs):
        print 'post_delete signal,', instance
        print 'instance.id is None: %s' % (instance.id == None)

post_delete_test = PostDeleteHandler()

__test__ = {'API_TESTS':"""

# Save up the number of connected signals so that we can check at the end
# that all the signals we register get properly unregistered (#9989)
>>> pre_signals = (len(models.signals.pre_save.receivers),
...                len(models.signals.post_save.receivers),
...                len(models.signals.pre_delete.receivers),
...                len(models.signals.post_delete.receivers))

>>> models.signals.pre_save.connect(pre_save_test)
>>> models.signals.post_save.connect(post_save_test)
>>> models.signals.pre_delete.connect(pre_delete_test)
>>> models.signals.post_delete.connect(post_delete_test)

# throw a decorator syntax receiver into the mix
>>> @receiver(models.signals.pre_save)
... def pre_save_decorator_test(signal, sender, instance, **kwargs):
...     print "pre_save signal decorator,", instance

# throw a decorator syntax receiver into the mix
>>> @receiver(models.signals.pre_save, sender=Car)
... def pre_save_decorator_sender_test(signal, sender, instance, **kwargs):
...     print "pre_save signal decorator sender,", instance

>>> p1 = Person(first_name='John', last_name='Smith')
>>> p1.save()
pre_save signal, John Smith
pre_save signal decorator, John Smith
post_save signal, John Smith
Is created

>>> p1.first_name = 'Tom'
>>> p1.save()
pre_save signal, Tom Smith
pre_save signal decorator, Tom Smith
post_save signal, Tom Smith
Is updated

# Car signal (sender defined)
>>> c1 = Car(make="Volkswagon", model="Passat")
>>> c1.save()
pre_save signal, Volkswagon Passat
pre_save signal decorator, Volkswagon Passat
pre_save signal decorator sender, Volkswagon Passat
post_save signal, Volkswagon Passat
Is created

# Calling an internal method purely so that we can trigger a "raw" save.
>>> p1.save_base(raw=True)
pre_save signal, Tom Smith
Is raw
pre_save signal decorator, Tom Smith
post_save signal, Tom Smith
Is updated
Is raw

>>> p1.delete()
pre_delete signal, Tom Smith
instance.id is not None: True
post_delete signal, Tom Smith
instance.id is None: False

>>> p2 = Person(first_name='James', last_name='Jones')
>>> p2.id = 99999
>>> p2.save()
pre_save signal, James Jones
pre_save signal decorator, James Jones
post_save signal, James Jones
Is created

>>> p2.id = 99998
>>> p2.save()
pre_save signal, James Jones
pre_save signal decorator, James Jones
post_save signal, James Jones
Is created

>>> p2.delete()
pre_delete signal, James Jones
instance.id is not None: True
post_delete signal, James Jones
instance.id is None: False

>>> Person.objects.all()
[<Person: James Jones>]

>>> models.signals.post_delete.disconnect(post_delete_test)
>>> models.signals.pre_delete.disconnect(pre_delete_test)
>>> models.signals.post_save.disconnect(post_save_test)
>>> models.signals.pre_save.disconnect(pre_save_test)
>>> models.signals.pre_save.disconnect(pre_save_decorator_test)
>>> models.signals.pre_save.disconnect(pre_save_decorator_sender_test, sender=Car)

# Check that all our signals got disconnected properly.
>>> post_signals = (len(models.signals.pre_save.receivers),
...                 len(models.signals.post_save.receivers),
...                 len(models.signals.pre_delete.receivers),
...                 len(models.signals.post_delete.receivers))

>>> pre_signals == post_signals
True

"""}
