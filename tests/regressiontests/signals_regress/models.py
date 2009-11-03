"""
Testing signals before/after saving and deleting.
"""

from django.db import models

class Author(models.Model):
    name = models.CharField(max_length=20)

    def __unicode__(self):
        return self.name

class Book(models.Model):
    name = models.CharField(max_length=20)
    authors = models.ManyToManyField(Author)

    def __unicode__(self):
        return self.name

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

def post_delete_test(signal, sender, instance, **kwargs):
    print 'post_delete signal,', instance
    print 'instance.id is not None: %s' % (instance.id != None)

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

>>> a1 = Author(name='Neal Stephenson')
>>> a1.save()
pre_save signal, Neal Stephenson
post_save signal, Neal Stephenson
Is created

>>> b1 = Book(name='Snow Crash')
>>> b1.save()
pre_save signal, Snow Crash
post_save signal, Snow Crash
Is created

# Assigning to m2m shouldn't generate an m2m signal
>>> b1.authors = [a1]

# Removing an author from an m2m shouldn't generate an m2m signal
>>> b1.authors = []

>>> models.signals.post_delete.disconnect(post_delete_test)
>>> models.signals.pre_delete.disconnect(pre_delete_test)
>>> models.signals.post_save.disconnect(post_save_test)
>>> models.signals.pre_save.disconnect(pre_save_test)

# Check that all our signals got disconnected properly.
>>> post_signals = (len(models.signals.pre_save.receivers),
...                 len(models.signals.post_save.receivers),
...                 len(models.signals.pre_delete.receivers),
...                 len(models.signals.post_delete.receivers))

>>> pre_signals == post_signals
True

"""}
