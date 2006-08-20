from django.contrib.admin import utils
from django import forms, template
from django.shortcuts import render_to_response, get_object_or_404
from django.http import Http404, HttpResponse, HttpResponseRedirect
from django.contrib.contenttypes.models import ContentType
from django.contrib.auth.models import RowLevelPermission, User, Group
from django.db import models
from django.contrib.admin.row_level_perm_manipulator import AddRLPManipulator, ChangeRLPManipulator
from django.core.exceptions import ImproperlyConfigured, ObjectDoesNotExist, PermissionDenied
from django.core.paginator import ObjectPaginator, InvalidPage
from django.contrib.admin.views.main import unquote, quote
from django.contrib.admin.views.decorators import staff_member_required
from django.views.decorators.cache import never_cache


def view_row_level_permissions(request, app_label, model_name, object_id):
    model = models.get_model(app_label, model_name)
    object_id = unquote(object_id)
    
    model_ct = ContentType.objects.get_for_model(model)
    model_instance = get_object_or_404(model, pk=object_id)
    opts = model_instance._meta
    
    if not opts.row_level_permissions:
        raise Http404
    
    if not request.user.has_perm(opts.app_label + '.' + opts.get_change_permission(), object=model_instance):
        raise PermissionDenied
    if not request.user.has_perm(RowLevelPermission._meta.app_label + '.' + RowLevelPermission._meta.get_change_permission()):
        raise PermissionDenied    
    
    c = template.RequestContext(request, {
        'title': _('Edit Row Level Permissions'),
        'object_id': object_id,
        'content_type_id':model_ct.id,
        'original': model_instance,
        'opts':opts,
    })   

    
    list_per_page = opts.admin.list_per_page
    #list_per_page = 20
    paginator = ObjectPaginator(model_instance.row_level_permissions.order_by('owner_ct', 'owner_id'),
                                list_per_page)
    page = int(request.GET.get('page', 1))-1
    rlp_list = paginator.get_page(page)    
    paginator_context = {
        "is_paginated": paginator.has_next_page(0),
        "has_next": paginator.has_next_page(page),
        "has_previous": paginator.has_previous_page(page),
        "page": page+1,
        "next": page+2,
        "previous": page,
        "hits":paginator.hits,
        "results_per_page":list_per_page,
        "pages":paginator.pages,
        "has_next":paginator.has_next_page(page),
        "has_previous":paginator.has_previous_page(page),
    }
    c.update(paginator_context)
    
    rlp_errors = rlp_new_data = {}
    add_rlp_manip = AddRLPManipulator(model_instance, model_ct)
    edit_rlp_manip = ChangeRLPManipulator(model_ct)
    new_rlp_form = forms.FormWrapper(add_rlp_manip, rlp_new_data, rlp_errors)
    
    user_rlp_form_list = []
    other_rlp_form_list = []
    group_rlp_form_list = []

    group_ct = model_ct = ContentType.objects.get_for_model(Group)
    user_ct = model_ct = ContentType.objects.get_for_model(User)
    for r in rlp_list:
        owner_val = str(r.owner_ct)+"-"+str(r.owner_id)
        data = {'id':r.id, 'owner':owner_val, 'perm':r.permission.id, 'negative':r.negative}
        
        if r.owner_ct.id is user_ct.id:
            user_rlp_form_list.append({'form':forms.FormWrapper(edit_rlp_manip, data, rlp_errors), 'rlp':r})
        elif r.owner_ct.id is group_ct.id:
            group_rlp_form_list.append({'form':forms.FormWrapper(edit_rlp_manip, data, rlp_errors), 'rlp':r})            
        else:
            other_rlp_form_list.append({'form':forms.FormWrapper(edit_rlp_manip, data, rlp_errors), 'rlp':r})
    
    rlp_forms = []
    if user_rlp_form_list:
        rlp_forms.append((_('Users'), user_rlp_form_list,))
    if group_rlp_form_list:
        rlp_forms.append((_('Groups'), group_rlp_form_list,))
    if other_rlp_form_list:
        rlp_forms.append((_('Other'), other_rlp_form_list,))

    rlp_context = {'new_rlp_form':new_rlp_form, 
               'rlp_forms':rlp_forms, }
    
    c.update(rlp_context)
    
    return render_to_response([
        "admin/%s/%s/row_level_permission.html" % (opts.app_label, opts.object_name.lower()),
        "admin/%s/row_level_permission.html" % opts.app_label,
        "admin/row_level_permission.html"], context_instance=c)

view_row_level_permissions = staff_member_required(never_cache(view_row_level_permissions))

def delete_row_level_permission(request, app_label, model_name, object_id, ct_id, rlp_id, hash):
    msg = {}
    
    if utils.verify_objref_hash(ct_id, rlp_id, hash):
        model = models.get_model(app_label, model_name)
        object_id = unquote(object_id)
        
        model_ct = ContentType.objects.get_for_model(model)
        model_instance = get_object_or_404(model, pk=object_id)
        rlp = get_object_or_404(RowLevelPermission, pk=rlp_id)
        ct = rlp.model_ct
        obj = rlp.model

        if model_instance.id is not obj.id:
            raise PermissionDenied

        if not request.user.has_perm(rlp._meta.app_label + '.' + rlp._meta.get_delete_permission()):
            raise PermissionDenied   
        if not request.user.has_perm(obj._meta.app_label + '.' + obj._meta.get_change_permission(), object=obj):
            raise PermissionDenied           

        rlp.delete()
        msg = {"result":True, "text":_("Row level permission was successful deleted"), "id":rlp_id}
    else:
        msg = { 'result':False, 'text': _("row level permission not found (bad hash)" )}

    request.user.message_set.create(message=msg['text'])

    return HttpResponseRedirect(request.META["HTTP_REFERER"])
#    return HttpResponseRedirect("%s?rlp_result=%s&rlp_msg=%s" % (request.META["HTTP_REFERER"], str(msg["result"]), main.quote(msg["text"])))
    #return main.change_stage(request, main.quote(obj._meta.app_label), main.quote(obj._meta.object_name),
    #                    main.quote(str(obj.id)), extra_context={"row_level_perm_msg":msg,})
delete_row_level_permission = staff_member_required(never_cache(delete_row_level_permission))

def add_row_level_permission(request, app_label, model_name, object_id):
    msg = {}
    if not request.POST:
        msg = { 'result':False, 'text': _("Only POSTs are allowed" )} 

        request.user.message_set.create(message=msg['text'])
        return HttpResponseRedirect("/edit/%s/%s" % (obj_type, object_id))  

    model = models.get_model(app_label, model_name)
    object_id = unquote(object_id)
    
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
    if msg["result"]:
        request.user.message_set.create(message=msg['text']) 
        return HttpResponseRedirect(request.META["HTTP_REFERER"])
    else:
        return HttpResponseRedirect("../?err_msg=%s" % msg['text'])
add_row_level_permission = staff_member_required(never_cache(add_row_level_permission))

def change_row_level_permission(request, app_label, model_name, object_id, ct_id, rlp_id, hash):
    msg = {}
    if not request.POST:
        msg = { 'result':False, 'text': _("Only POSTs are allowed" )}  

    if not utils.verify_objref_hash(ct_id, rlp_id, hash):
        msg = { 'result':False, 'text': _("row level permission not found (bad hash)" )}           
    
    if msg.has_key("result"):
        request.user.message_set.create(message=msg['text'])
        return HttpResponseRedirect('../../../../')
    
    model = models.get_model(app_label, model_name)
    object_id = unquote(object_id)
    
    ct = ContentType.objects.get_for_model(model)
    model_instance = get_object_or_404(model, pk=object_id)    
    
    rlp = get_object_or_404(RowLevelPermission, pk=rlp_id)
    opts = rlp._meta
    if not request.user.has_perm(opts.app_label + '.' + opts.get_add_permission()):
        raise PermissionDenied  

    obj = rlp.model
    if model_instance.id is not obj.id:
        raise PermissionDenied
    
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
        
    request.user.message_set.create(message=msg['text']) 
    return HttpResponseRedirect(request.META["HTTP_REFERER"])
#    request.POST = {}
#    return change_stage(request, main.quote(obj._meta.app_label), main.quote(obj._meta.object_name),
#                    main.quote(str(obj.id)), extra_context={"row_level_perm_msg":msg,})

change_row_level_permission = staff_member_required(never_cache(change_row_level_permission))