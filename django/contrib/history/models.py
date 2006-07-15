from django.db import models
from django.db.models import signals
from django.dispatch import dispatcher
from django.contrib.auth.models import User
from tut1.polls.models import Poll #Temp import of used models
# Misc stuff
import cPickle as Pickle
from datetime import datetime
#from django.contrib.history.api import get_object, save_new_revision

class ChangeLog(models.Model):
    change_time = models.DateTimeField(_('time of change'), auto_now=True)
    parent = models.ForeignKey(Poll)
    user = models.ForeignKey(User, default="1")
    object = models.TextField()
    #object_type = models.CharField(maxlength=50)
    #pub_date = models.DateTimeField('date published')
    
    class Meta:
	verbose_name = _('changelog entry')
	verbose_name_plural = _('changelog entries')
	db_table = _('history_changelog')
	
    class Admin:
	fields = (
	    ('Meta info', {'fields': ('change_time', 'parent', 'user',)}),
	    ('Object', {'fields': ('object',),}),
	)

	list_display = ('parent', 'user', 'change_time')

    def get_object(self):
	""" Returns unpickled object. """
	return Pickle.loads(self.object)

    def get_revision_number(self):
	""" Returns the ID/revision number of ChangeLog entry. """
	return self.id

################
# Other (API) methods
################

def get_version(object, offset=1):
    """ Returns 'current-offset' revision of the 'object' """
    list = ChangeLog.objects.order_by('-id').filter(parent=object.id)[offset]
    print list.get_object()
    return list

def list_history(parent_id, *args):
    """ Returns a list of all revisions for that id. """
    if args:
	return ChangeLog.objects.filter(parent=parent_id)[:args[0]]
	#print "extra"
	#return ChangeLog.objects.filter(parent=parent_id)
    else:
	return ChangeLog.objects.filter(parent=parent_id)

def version(object, num=5):
    """ Returns last 'num' revisions of the 'object'. """
    return ChangeLog.objects.order_by('-id').filter(parent=object.id)[:num]

def version_by_date(object, date):
    """ Returns a list of revisions made at 'date'. """
    return ChangeLog.objects.filter(parent=object.id).filter(change_time__exact=date)


def save_new_revision(sender, instance, signal, *args, **kwargs):
    """ Saves a old copy of the record into the History table."""
    #modelname = instance.__class__.__name__
    #print modelname
    old = Poll.objects.filter(pk=instance.id)
    log = ChangeLog()
    log.parent_id = instance.id
    #log.user_id = .user_id
    log.object = Pickle.dumps(old[0], protocol=0)
    log.save()
    print "New change saved."

def _get_first_revision(object):
    pass


dispatcher.connect( save_new_revision, signal=signals.pre_save, sender=Poll )
