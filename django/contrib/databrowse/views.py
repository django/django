from django.db.models import FieldDoesNotExist, DateTimeField
from django.http import Http404
from django.shortcuts import render_to_response
from django.contrib.databrowse.datastructures import EasyModel, EasyChoice
import datetime
import time

###########
# CHOICES #
###########

def choice_list(request, app_label, module_name, field_name, models):
    m, f = lookup_field(app_label, module_name, field_name, models)
    return render_to_response('databrowse/choice_list.html', {'model': m, 'field': f})

def choice_detail(request, app_label, module_name, field_name, field_val, models):
    m, f = lookup_field(app_label, module_name, field_name, models)
    try:
        label = dict(f.field.choices)[field_val]
    except KeyError:
        raise Http404('Invalid choice value given')
    obj_list = m.objects(**{f.field.name: field_val})
    return render_to_response('databrowse/choice_detail.html', {'model': m, 'field': f, 'value': label, 'object_list': obj_list})
