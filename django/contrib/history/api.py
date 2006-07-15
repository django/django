from django.db import models
from django.db.models import signals
from django.dispatch import dispatcher
#from django.shortcuts import get_object_or_404
from django.contrib.history.models import ChangeLog
import cPickle as Pickle
from tut1.polls.models import Poll #Temp import of used models

def get_object(change):
    """ Returns unpickled object. """
    return Pickle.loads(change.object)

def get_revision_number(change):
    """ Returns the ID/revision number of ChangeLog entry. """
    return change.id

def get_revision():
    pass

def list_history(type, parent_id):
    return type.objects.all().filter(pk=parent_id)

def version(num=-1):
    pass

def save_new_revision(sender, instance, signal, *args, **kwargs):
    """ Saves a current copy of the record into the History table."""
    log = ChangeLog()
    log.parent_id = instance.id
    #log.user_id = .user_id
    log.object = Pickle.dumps(instance, protocol=0)
    log.save()
    print "New change saved."

def _get_original_object(type, id):
    pass


dispatcher.connect( save_new_revision, signal=signals.post_save, sender=Poll )
