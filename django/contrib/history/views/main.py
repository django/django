from django.db import models
#from django.db.models import get_models
#from django.utils.text import capfirst
from django.contrib.history.models import ChangeLog
from django.http import HttpResponse
from django.shortcuts import get_object_or_404, render_to_response
from datetime import datetime
#import cPickle as Pickle
#from django.contrib.history.api import get_object, list_history

def index(request):
    changes_list = ChangeLog.objects.all()
    return render_to_response('history/list.html', 
			      {'changes_list': changes_list})

def list(request):
    changes_list = ChangeLog.objects.all()
    return render_to_response('history/list.html', 
			      {'changes_list': changes_list})


def detail(request, change_id):
    change = get_object_or_404(ChangeLog, pk=change_id)
    object = change.get_object()


    ch1 = ChangeLog.objects.version_by_date(object, datetime(2006, 8, 21))
    print "Change1: ",ch1

    ch2 = ChangeLog.objects.get_version(object)
    print "Change2: ",ch2

    ch3 = ChangeLog.objects.list_history(object, offset=1)
    print "Change3: ",ch3

    return render_to_response('history/detail.html', {'change': change,
						      'object': object,
						      'change_fields': change._meta.fields,
						      'object_fields': object._meta.fields,})

def changes(request, parent_id):
    changes_list = ChangeLog.objects.list_history(parent, offset=3)
    return render_to_response('history/list.html',
			      {'changes_list': changes_list})
