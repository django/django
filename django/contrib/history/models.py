from django.db import models
from django.db.models import signals, get_models
from django.dispatch import dispatcher
from django.contrib.auth.models import User
from django.contrib.contenttypes.models import ContentType
#from tut1.polls.models import Poll, Choice #Temp import of used models
# Misc stuff
import cPickle as Pickle
from datetime import datetime
#from django.utils.text import capfirst

CHANGE_TYPES = (
    ('A', 'Addition'),
    ('U', 'Update'),
    ('D', 'Deletion'),
)

#########################
# Manager - API methods #
#########################

class ChangeLogManager(models.Manager):

    def get_version(self, object, **kwargs):
	""" 
	Returns 'current-offset' revision of the 'object' 
	"""
	if not kwargs or not kwargs['offset']: offset=0

	ct = ContentType.objects.get_for_model(object)

	if kwargs and kwargs['revision']:
	    return self.get_query_set().filter(
		content_type=ct.id).filter(
		    object_id=object.id).filter(
			pk=revision)[offset]
	else:
	    return self.get_query_set().filter(
		content_type=ct.id).filter(
		    object_id=object.id)[offset]

    def list_history(self, object, **kwargs):
	""" 
	list_history(object): Returns a list of all revisions for that id.
	list_history(object, offset=X): Returns a list of last X revisions.    
	"""
	ct = ContentType.objects.get_for_model(object)
	if kwargs['offset']:
	    return self.get_query_set().filter(
		content_type=ct.id).filter(
		    object_id=object.id)[:kwargs['offset']]
	else:
	    return ChangeLog.objects.filter(object_id=object.id)

    def version_by_date(self, object, date):
	""" 
	Returns a list of revisions made at 'date'. 
	"""
	ct = ContentType.objects.get_for_model(object)
	return self.get_query_set().filter(
	    content_type=ct.id).filter(
		change_time__exact=date)

########################
# Generic change model #
########################

class ChangeLog(models.Model):
    change_time = models.DateTimeField (_('time of change'), auto_now=True)
    content_type = models.ForeignKey(ContentType)
    parent = models.GenericForeignKey()
    object_id = models.IntegerField(_('object ID'))
    user = models.ForeignKey(User, default="1")
    change_type = models.CharField(maxlength=1, choices=CHANGE_TYPES)
    object = models.TextField()
    comment = models.CharField(maxlength=250, blank=True)

    objects = ChangeLogManager()
    
    class Meta:
	verbose_name = _('changelog entry')
	verbose_name_plural = _('changelog entries')
	db_table = _('django_history_log')
	
    class Admin:
	date_hierarchy = 'change_time'
	list_filter = ['change_time',  'change_type', 'content_type']
	fields = (
	    ('Meta info', {'fields': ('change_time', 'content_type', 'object_id', 'user', 'comment'),}),
	    ('Object', {'fields': ('object',),}),
	)

	list_display = ('__str__', 'user', 'change_type','comment', 'content_type', 'change_time', )
	
    def __str__(self):
	return str(self.get_object())

    def get_object(self):
	""" Returns unpickled object. """
	return Pickle.loads(self.object)

    def get_rev_num(self):
	""" Returns the ID/revision number of ChangeLog entry. """
	return self.id	

#########################
# Pre-save signal catch #
#########################

def _import_models(instance):
    """ 
    Checks for models that are history-enabled and imports the one of
    which "instance" is an instance of.

    Returns "import object" if import went fine.
    """
    model_list = []
    m = None

    for model in models.get_models():
	try:
	    if model.History:
		model_list.append({'module': model.__module__,
				   'name': model.__name__})
	except:
	    pass

    for model in model_list:
	if model['name'] is instance.__class__.__name__:
	    try:
		m = __import__(model['module'], '', '', [model['name']])
		#print model['module'],": ",model['name'],"- ",m
		print "Model import done: ",m
	    except:
		print "Model import error."
		return False

    return m

def save_new_revision(sender, instance, signal, *args, **kwargs):
    """ 
    Saves a old copy of the record into the History table.

    If the instance does not have an ID then it is a new record and saved as such.
    If the instance is passed with signal_name='pre_save' it saves a previous
    version (taken from the database).
    If the instance is passed with signal_name='pre_delete' it saves the instance
    as the latest revision.

    """
    print "Sender: ",sender
    print "Signal: ",kwargs['signal_name']

    if instance.__class__.__name__ is 'ChangeLog' or not hasattr(instance, 'History'): 
	print "Not history-enabled class."
	return 0

    #instance_name = instance.__class__.__name__
    #print instance_name
    im = _import_models(instance)
    old = None
    log = None
    
    if im:
	try:
	    if kwargs['signal_name'] is 'pre_delete':
		print "Instance was last revision."
		old = instance
		log = ChangeLog(parent=instance, change_type='D', comment="Object deleted. Last revision.")
	    elif ((kwargs['signal_name'] is 'pre_save') and instance.id):
		print "Instance has an ID."
		old = getattr(im, instance.__class__.__name__).objects.filter(pk=instance.id)[0]
		log = ChangeLog(parent=instance, change_type='U', comment="Update")
	    else:
		print "Instance without an ID."
		old = instance
		instance.id = 0	# FIX: ID cannot be None
		log = ChangeLog(parent=instance, change_type='A', comment="New")
	except:
	    return 1
    else:
	return 0  # exit wo/ an action

    # DEBUG
    #print "Old: ",old
    #print "Instance: ",instance.id
    #print "Test: ",getattr(instance, 'Admin').date_hierarchy
    #print "Log: ",log.change_time

    try: 
	log.object = Pickle.dumps(old, protocol=0)
	log.save()
	print "New change saved."
    except:
	print "ChangeLog faild to save changes."


dispatcher.connect( save_new_revision, signal=signals.pre_save )
dispatcher.connect( save_new_revision, signal=signals.pre_delete )
