from django.contrib.admin import utils
from django.shortcuts import render_to_response, get_object_or_404
from django.http import Http404, HttpResponse, HttpResponseRedirect
from django.contrib.contenttypes.models import ContentType
from django.contrib.auth.models import RowLevelPermission
from django.contrib.admin.row_level_perm_manipulator import AddRLPManipulator, ChangeRLPManipulator
from django.core.exceptions import ImproperlyConfigured, ObjectDoesNotExist, PermissionDenied
import simplejson

def delete_row_level_permission(request, ct_id, rlp_id, hash):
    msg = {}
    ajax = request.GET.has_key("ajax")
    if utils.verify_objref_hash(ct_id, rlp_id, hash):
        rlp = get_object_or_404(RowLevelPermission, pk=rlp_id)
        ct = rlp.model_ct
        obj = rlp.model
        opts = rlp._meta
        if not request.user.has_perm(opts.app_label + '.' + opts.get_delete_permission()):
            raise PermissionDenied   
        if not request.user.has_perm(obj._meta.app_label + '.' + obj._meta.get_change_permission()):
            raise PermissionDenied           
        rlp.delete()
        msg = {"result":True, "text":_("Row level permission was successful deleted"), "id":rlp_id}
    else:
        msg = { 'result':False, 'text': _("row level permission not found (bad hash)" )}
    if ajax:
        return HttpResponse(simplejson.dumps(msg), 'text/javascript')
    request.user.message_set.create(message=msg['text'])
    #return HttpResponseRedirect("/edit/%s/%s" % (ct.model, obj.id))
    return HttpResponseRedirect("../../../../../../%s/%s/%s" % (obj._meta.app_label, obj._meta.module_name , str(obj.id)))

def add_row_level_permission(request, ct_id, obj_id):
    msg = {}
    ajax = request.GET.has_key("ajax")
    if not request.POST:
        msg = { 'result':False, 'text': _("Only POSTs are allowed" )} 
        if ajax:
            return HttpResponse(simplejson.dumps(msg), 'text/javascript')
        request.user.message_set.create(message=msg['text'])
        return HttpResponseRedirect("/edit/%s/%s" % (obj_type, obj_id))  

    ct = get_object_or_404(ContentType, pk=ct_id)
    obj = get_object_or_404(ct.model_class(), pk=obj_id)
    if not request.user.has_perm(obj._meta.app_label + '.' + obj._meta.get_change_permission()):
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
    if not ajax:
        request.user.message_set.create(message=msg['text'])
        return HttpResponseRedirect("../../../../../%s/%s/%s" % (obj._meta.app_label, obj._meta.module_name , str(obj.id)))
    
    
    resp_list = []
    for rlp in rlp_list:
        hash = utils.create_objref(rlp)
        resp_list.append({"id":rlp.id, "permission":rlp.permission.id, "hash":hash})
    msg["results"]=resp_list
    return HttpResponse(simplejson.dumps(msg), 'text/javascript')

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

    object_model = rlp.model_ct.model_class()
    if not request.user.has_perm(object_model._meta.app_label + '.' + object_model._meta.get_change_permission()):
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
    request.user.message_set.create(message=msg['text'])
    return HttpResponseRedirect("../../../../../../%s/%s/%s" % (object_model._meta.app_label, object_model._meta.module_name , str(rlp.model_id)))