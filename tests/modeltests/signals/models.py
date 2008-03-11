"""
Testing signals before/after saving and deleting.
"""

from django.db import models
from django.dispatch import dispatcher

class Person(models.Model):
    first_name = models.CharField(max_length=20)
    last_name = models.CharField(max_length=20)

    def __unicode__(self):
        return u"%s %s" % (self.first_name, self.last_name)


def pre_save_nokwargs_test(sender, instance):
    print 'pre_save_nokwargs signal'

def post_save_nokwargs_test(sender, instance):
    print 'post_save_nokwargs signal'

def pre_save_test(sender, instance, **kwargs):
    print 'pre_save signal,', instance
    if kwargs.get('raw'):
        print 'Is raw'

def post_save_test(sender, instance, **kwargs):
    print 'post_save signal,', instance
    if 'created' in kwargs:
        if kwargs['created']:
            print 'Is created'
        else:
            print 'Is updated'
    if kwargs.get('raw'):
        print 'Is raw'

def pre_delete_test(sender, instance, **kwargs):
    print 'pre_delete signal,', instance
    print 'instance.id is not None: %s' % (instance.id != None)

def post_delete_test(sender, instance, **kwargs):
    print 'post_delete signal,', instance
    print 'instance.id is None: %s' % (instance.id == None)

__test__ = {'API_TESTS':"""
>>> dispatcher.connect(pre_save_nokwargs_test, signal=models.signals.pre_save)
>>> dispatcher.connect(post_save_nokwargs_test, signal=models.signals.post_save)
>>> dispatcher.connect(pre_save_test, signal=models.signals.pre_save)
>>> dispatcher.connect(post_save_test, signal=models.signals.post_save)
>>> dispatcher.connect(pre_delete_test, signal=models.signals.pre_delete)
>>> dispatcher.connect(post_delete_test, signal=models.signals.post_delete)

>>> p1 = Person(first_name='John', last_name='Smith')
>>> p1.save()
pre_save_nokwargs signal
pre_save signal, John Smith
post_save_nokwargs signal
post_save signal, John Smith
Is created

>>> p1.first_name = 'Tom'
>>> p1.save()
pre_save_nokwargs signal
pre_save signal, Tom Smith
post_save_nokwargs signal
post_save signal, Tom Smith
Is updated

# Calling an internal method purely so that we can trigger a "raw" save.
>>> p1.save_base(raw=True)
pre_save_nokwargs signal
pre_save signal, Tom Smith
Is raw
post_save_nokwargs signal
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
pre_save_nokwargs signal
pre_save signal, James Jones
post_save_nokwargs signal
post_save signal, James Jones
Is created

>>> p2.id = 99998
>>> p2.save()
pre_save_nokwargs signal
pre_save signal, James Jones
post_save_nokwargs signal
post_save signal, James Jones
Is created

>>> p2.delete()
pre_delete signal, James Jones
instance.id is not None: True
post_delete signal, James Jones
instance.id is None: False

>>> Person.objects.all()
[<Person: James Jones>]

>>> dispatcher.disconnect(pre_save_nokwargs_test, signal=models.signals.pre_save)
>>> dispatcher.disconnect(post_save_nokwargs_test, signal=models.signals.post_save)
>>> dispatcher.disconnect(post_delete_test, signal=models.signals.post_delete)
>>> dispatcher.disconnect(pre_delete_test, signal=models.signals.pre_delete)
>>> dispatcher.disconnect(post_save_test, signal=models.signals.post_save)
>>> dispatcher.disconnect(pre_save_test, signal=models.signals.pre_save)
"""}
