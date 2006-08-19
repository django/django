from django.contrib.admin import utils
from django import forms, template
from django.shortcuts import render_to_response, get_object_or_404
from django.http import Http404, HttpResponse, HttpResponseRedirect
from django.contrib.contenttypes.models import ContentType
from django.contrib.auth.models import RowLevelPermission
from django.contrib.admin.views import main
from django.db import models
from django.contrib.admin.row_level_perm_manipulator import AddRLPManipulator, ChangeRLPManipulator
from django.core.exceptions import ImproperlyConfigured, ObjectDoesNotExist, PermissionDenied
from django.core.paginator import ObjectPaginator, InvalidPage
import simplejson

def edit_row_level_permissions(request, app_label, model_name, object_id):
    model = models.get_model(app_label, model_name)
    object_id = main.unquote(object_id)
    
    model_ct = ContentType.objects.get_for_model(model)
    model_instance = get_object_or_404(model, pk=object_id)
    opts = model_instance._meta
    
    if not opts.row_level_permissions:
        raise Http404
    
    if not request.user.has_perm(opts.app_label + '.' + opts.get_change_permission(), object=model_instance):
        raise PermissionDenied
    if not request.user.has_perm(RowLevelPermission._meta.app_label + '.' + RowLevelPermission._meta.get_change_permission()):
        raise PermissionDenied    
    
    #TODO: For now takes the number per page from the model instance not the RLP object
    paginator = ObjectPaginator(model_instance.row_level_permissions.order_by('owner_ct', 'owner_id'),
                                opts.admin.list_per_page)
    
    page = int(request.GET.get('page', 0))
    rlp_list = paginator.get_page(page)

    c = template.RequestContext(request, {
        'title': _('Edit Row Level Permissions'),
        'object_id': object_id,
        'content_type_id':model_ct.id,
        'original': model_instance,
        'opts':opts,
        "is_paginated": paginator.has_next_page(0),
        "has_next": paginator.has_next_page(page),
        "has_previous": paginator.has_previous_page(page),
        "page": page + 1,
        "next": page + 1,
        "previous": page - 1,
    })   
    
    rlp_errors = rlp_new_data = {}
    add_rlp_manip = AddRLPManipulator(model_instance, model_ct)
    edit_rlp_manip = ChangeRLPManipulator(model_ct)
    new_rlp_form = forms.FormWrapper(add_rlp_manip, rlp_new_data, rlp_errors)
    empty_rlp_form = forms.FormWrapper(edit_rlp_manip, rlp_new_data, rlp_errors)
    rlp_form_list = []
    for r in rlp_list:
        owner_val = str(r.owner_ct)+"-"+str(r.owner_id)
        data = {'id':r.id, 'owner':owner_val, 'perm':r.permission.id, 'negative':r.negative}
        rlp_form_list.append({'form':forms.FormWrapper(edit_rlp_manip, data, rlp_errors), 'rlp':r})
    rlp_context = {'new_rlp_form':new_rlp_form, 
               'rlp_form_list':rlp_form_list, 
               'empty_rlp_form':empty_rlp_form,}
    
    c.update(rlp_context)
    
    return render_to_response([
        "admin/%s/%s/row_level_permission.html" % (opts.app_label, opts.object_name.lower()),
        "admin/%s/row_level_permission.html" % opts.app_label,
        "admin/row_level_permission.html"], context_instance=c)

def delete_row_level_permission(request, ct_id, rlp_id, hash):
    msg = {}
    if utils.verify_objref_hash(ct_id, rlp_id, hash):
        rlp = get_object_or_404(RowLevelPermission, pk=rlp_id)
        ct = rlp.model_ct
        obj = rlp.model

        if not request.user.has_perm(rlp._meta.app_label + '.' + rlp._meta.get_delete_permission()):
            raise PermissionDenied   
        if not request.user.has_perm(obj._meta.app_label + '.' + obj._meta.get_change_permission(), object=obj):
            raise PermissionDenied           

        rlp.delete()
        msg = {"result":True, "text":_("Row level permission was successful deleted"), "id":rlp_id}
    else:
        msg = { 'result':False, 'text': _("row level permission not found (bad hash)" )}

    request.user.message_set.create(message=result['text'])

    return HttpResponseRedirect("../")
#    return HttpResponseRedirect("%s?rlp_result=%s&rlp_msg=%s" % (request.META["HTTP_REFERER"], str(msg["result"]), main.quote(msg["text"])))
    #return main.change_stage(request, main.quote(obj._meta.app_label), main.quote(obj._meta.object_name),
    #                    main.quote(str(obj.id)), extra_context={"row_level_perm_msg":msg,})


def add_row_level_permission(request, app_label, model_name, object_id):
    msg = {}
    if not request.POST:
        msg = { 'result':False, 'text': _("Only POSTs are allowed" )} 

        request.user.message_set.create(message=msg['text'])
        return HttpResponseRedirect("/edit/%s/%s" % (obj_type, object_id))  

    model = models.get_model(app_label, model_name)
    object_id = main.unquote(object_id)
    
    ct = ContentType.objects.get_for_model(model)
    obj = get_object_or_404(model, pk=object_id)
    
    if not request.user.has_perm(obj._meta.app_label + '.' + obj._meta.get_change_permission(), object=obj):
        raise PermissionDenied  

    if not request.user.has_perm(RowLevelPermission._meta.app_label + '.' + RowLevelPermission._meta.get_add_permission()):
        raise PermissionDenied
    
    manip = AddRLPManipulator(obj, ct)
    
    new_data = request.POST.copy()
    
    manip.do_html2python(new_data)
    
    rlp_list = []
    from django.core import validators
    try:
        rlp_list = manip.save(new_data)
    except validators.ValidationError:
        msg = {"result":False, "text":_("A row level permission already exists with the specified values.")}
    else:
        if len(rlp_list) is 1:
            msg = {"result":True, "text":_("Row level permission has successfully been added.")}
        else:
            msg = {"result":True, "text":_("Row level permissions have successfully been added.")}
    
    resp_list = []
    for rlp in rlp_list:
        hash = utils.create_objref(rlp)
        resp_list.append({"id":rlp.id, "permission":rlp.permission.id, "hash":hash})
    msg["results"]=resp_list

    #return main.change_stage(request, main.quote(obj._meta.app_label), main.quote(obj._meta.object_name),
    #                    main.quote(str(obj.id)), extra_context={"row_level_perm_msg":msg,})
    return HttpResponseRedirect("../")

def change_row_level_permission(request, ct_id, rlp_id, hash):    
    msg = {}
    ajax = request.GET.has_key("ajax")
    if not request.POST:
        msg = { 'result':False, 'text': _("Only POSTs are allowed" )}  

    if not utils.verify_objref_hash(ct_id, rlp_id, hash):
        msg = { 'result':False, 'text': _("row level permission not found (bad hash)" )}           
    
    if msg.has_key("result"):
        if ajax:
            return HttpResponse(simplejson.dumps(msg), 'text/javascript')
        request.user.message_set.create(message=msg['text'])
        return HttpResponseRedirect("/edit/%s/%s" % (obj_type, obj_id))         
    
    rlp = get_object_or_404(RowLevelPermission, pk=rlp_id)
    opts = rlp._meta
    if not request.user.has_perm(opts.app_label + '.' + opts.get_add_permission()):
        raise PermissionDenied  

    obj = rlp.model
    if not request.user.has_perm(rlp._meta.app_label + '.' + rlp._meta.get_change_permission(), object=obj):
        raise PermissionDenied
    
    manip = ChangeRLPManipulator()
    new_data = request.POST.copy()
    
    new_data["id"] = rlp_id
    manip.do_html2python(new_data)
    from django.core import validators
    try:
        new_rlp = manip.save(new_data)
    except validators.ValidationError:
        msg = {"result":False, "text":_("A row level permission already exists with the specified values")}
    else:
        msg = {"result":True, "text":_("Row level permission has successfully been changed"), "id":rlp_id}
    if ajax:
        return HttpResponse(simplejson.dumps(msg), 'text/javascript')
    
    request.POST = {}
    return main.change_stage(request, main.quote(obj._meta.app_label), main.quote(obj._meta.object_name),
                    main.quote(str(obj.id)), extra_context={"row_level_perm_msg":msg,})