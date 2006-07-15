from django.db import models
from django.db.models import get_models
from django.utils.text import capfirst
from django.contrib.history.models import ChangeLog, get_version, list_history, version_by_date
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
	print app['name']
	print app['models']

    changes_list = ChangeLog.objects.all()
    return render_to_response('history/list.html', 
			      {'changes_list': changes_list})


def detail(request, change_id):
    change = get_object_or_404(ChangeLog, pk=change_id)
    object = change.get_object()

    bla = version_by_date(object, datetime(2006, 6, 7))
    for b in bla:
	print b.change_time

    bla2 = get_version(object)

    return render_to_response('history/detail.html', {'change': change,
						      'object': object})

def changes(request, parent_id):
    changes_list = list_history(parent_id, 2)
    return render_to_response('history/list.html',
			      {'changes_list': changes_list})
