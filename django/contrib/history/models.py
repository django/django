from django.db import models
from django.db.models import signals, get_models
from django.dispatch import dispatcher
from django.contrib.auth.models import User
from django.contrib.contenttypes.models import ContentType
from tut1.polls.models import Poll #Temp import of used models
# Misc stuff
import cPickle as Pickle
from datetime import datetime
from django.utils.text import capfirst
#from django.contrib.history.api import get_object, save_new_revision

class ChangeLog(models.Model):
    change_time = models.DateTimeField (_('time of change'), auto_now=True)

    content_type = models.ForeignKey(ContentType)
    parent = models.GenericForeignKey()
    object_id = models.IntegerField(_('object ID'))
    #parent = models.ForeignKey(Poll)

    user = models.ForeignKey(User, default="1")
    object = models.TextField()
    comment = models.CharField(maxlength=250, default="Bla")

    #object_type = models.CharField(maxlength=50)
    #pub_date = models.DateTimeField('date published')
    
    class Meta:
	verbose_name = _('changelog entry')
	verbose_name_plural = _('changelog entries')
	db_table = _('history_changelog')
	
    class Admin:
	fields = (
	    ('Meta info', {'fields': ('change_time', 'content_type', 'object_id', 'user', 'comment'),}),
	    ('Object', {'fields': ('object',),}),
	)

	list_display = ('object_id', 'user', 'change_time')

    def get_object(self):
	""" Returns unpickled object. """
	return Pickle.loads(self.object)

    def get_revision_number(self):
	""" Returns the ID/revision number of ChangeLog entry. """
	return self.id

#######################
# Other (API) methods #
#######################

def get_version(object, offset=0):
    """ Returns 'current-offset' revision of the 'object' """
    list = ChangeLog.objects.order_by('-id').filter(object_id=object.id)[offset]
    print list.get_object()
    return list

def list_history(parent_id, **kwargs):
    """ 
    list_history(parent_id): Returns a list of all revisions for that id.
    list_history(parent_id, offset=X): Returns a list of last X revisions.    
    """
    if kwargs:
	list = ChangeLog.objects.filter(object_id=parent_id)[:kwargs['offset']]
	#for l in list:
	#    print l.parent.id
	return list
    else:
	return ChangeLog.objects.filter(object_id=parent_id)

#def version(object, num=5):
#    """ Returns last 'num' revisions of the 'object'. """
#    return ChangeLog.objects.order_by('-id').filter(parent=object.id)[:num]


def version_by_date(object, date):
    """ Returns a list of revisions made at 'date'. """
    return ChangeLog.objects.filter(object_id=object.id).filter(change_time__exact=date)


def get_all_models():
    app_list = []
    
    for app in models.get_apps():
	app_models = get_models(app)
	app_label = app_models[0]._meta.app_label

	model_list = []

	for m in app_models:
	    model_list.append({
		    'name': capfirst(m._meta.verbose_name_plural),
	    })

	if model_list:
	    model_list.sort()
	    app_list.append({
		    'name': app_label.title(),
		    'models': model_list,
            })

    for app in app_list:
	#print app['name']
	#print app['models']
	
	for m in app['models']:
	    print m['name']

#########################
# Pre-save signal catch #
#########################

def save_new_revision(sender, instance, signal, *args, **kwargs):
    """ Saves a old copy of the record into the History table."""
    #modelname = instance.__class__.__name__
    #print modelname
    old = Poll.objects.filter(pk=instance.id)
    print old
    if instance.History:
	print "Admin"
	print Poll._meta
    print instance.id
    log = ChangeLog(parent=instance)
    print log
    #log.parent_id = instance.id
    #log.user_id = .user_id
    log.object = Pickle.dumps(old[0], protocol=0)
    log.save()
    print "New change saved."

dispatcher.connect( save_new_revision, signal=signals.pre_save, sender=Poll )
