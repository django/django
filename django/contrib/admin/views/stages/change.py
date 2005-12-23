from django.contrib.admin.views.main import get_model_and_app
from django.core import formfields, template
from django.core.extensions import DjangoContext as Context
from django.contrib.admin.views.stages.modify import render_change_form
from django.db import models
from django.utils.text import capfirst, get_text_list
from django.utils.httpwrappers import HttpResponse, HttpResponseRedirect
from django.contrib.admin.views.decorators import staff_member_required
try:
    from django.contrib.admin.models import LogEntry, ADDITION, CHANGE, DELETION
except ImportError:
    raise ImproperlyConfigured, "You don't have 'django.contrib.admin' in INSTALLED_APPS."

from django.core.exceptions import Http404, ImproperlyConfigured, ObjectDoesNotExist

def log_change_message(user, opts, manipulator, new_object):
    pk_value = getattr(new_object, opts.pk.column)
    # Construct the change message.
    change_message = []
    if manipulator.fields_added:
        change_message.append(_('Added %s.') % get_text_list(manipulator.fields_added, _('and')))
    if manipulator.fields_changed:
        change_message.append(_('Changed %s.') % get_text_list(manipulator.fields_changed, _('and')))
    if manipulator.fields_deleted:
        change_message.append(_('Deleted %s.') % get_text_list(manipulator.fields_deleted, _('and')))
    change_message = ' '.join(change_message)
    if not change_message:
        change_message = _('No fields changed.')
    LogEntry.objects.log_action(user.id, opts.get_content_type_id(), pk_value, str(new_object), CHANGE, change_message)

def change_stage(request, path, object_id):
    model, app_label = get_model_and_app(path)
    opts = model._meta
    #mod, opts = _get_mod_opts(app_label, module_name)
    if not request.user.has_perm(app_label + '.' + opts.get_change_permission()):
        raise PermissionDenied
    if request.POST and request.POST.has_key("_saveasnew"):
        return add_stage(request, path, form_url='../../add/')
    
    try:
        manipulator = model.ChangeManipulator(object_id)
    except ObjectDoesNotExist:
        raise Http404

    if request.POST:
        new_data = request.POST.copy()
        if opts.has_field_type(models.FileField):
            new_data.update(request.FILES)

        errors = manipulator.get_validation_errors(new_data)

        manipulator.do_html2python(new_data)
        if not errors:
            if request.POST.has_key("command"):
                command_name = request.POST.get("command")
                manipulator.do_command(new_data, command_name)
                new_data = manipulator.flatten_data()
            elif not request.POST.has_key("_preview"):
                new_object = manipulator.save(new_data)
                log_change_message(request.user, opts, manipulator, new_object)
                msg = _('The %(name)s "%(obj)s" was changed successfully.') % {'name': opts.verbose_name, 'obj': new_object}
                pk_value = getattr(new_object, opts.pk.attname)
                if request.POST.has_key("_continue"):
                    request.user.add_message(msg + ' ' + _("You may edit it again below."))
                    if request.REQUEST.has_key('_popup'):
                        return HttpResponseRedirect(request.path + "?_popup=1")
                    else:
                        return HttpResponseRedirect(request.path)
                elif request.POST.has_key("_saveasnew"):
                    request.user.add_message(_('The %(name)s "%(obj)s" was added successfully. You may edit it again below.') % {'name': opts.verbose_name, 'obj': new_object})
                    return HttpResponseRedirect("../../%s/" % pk_value)
                elif request.POST.has_key("_addanother"):
                    request.user.add_message(msg + ' ' + (_("You may add another %s below.") % opts.verbose_name))
                    return HttpResponseRedirect("../../add/")
                else:
                    request.user.add_message(msg)
                    return HttpResponseRedirect("../../")
    else:
        # Populate new_data with a "flattened" version of the current data.
        new_data = manipulator.flatten_data()
        # TODO: do this in flatten_data...
        # If the object has ordered objects on its admin page, get the existing
        # order and flatten it into a comma-separated list of IDs.

        id_order_list = []
        for rel_obj in opts.get_ordered_objects():
            id_order_list.extend(getattr(manipulator.original_object, 'get_%s_order' % rel_obj.object_name.lower())())
        if id_order_list:
            new_data['order_'] = ','.join(map(str, id_order_list))
        errors = {}

    # Populate the FormWrapper.
    form = formfields.FormWrapper(manipulator, new_data, errors, edit_inline = True)
    form.original = manipulator.original_object
    form.order_objects = []

    #TODO Should be done in flatten_data  / FormWrapper construction
    for related in opts.get_followed_related_objects():
        wrt = related.opts.order_with_respect_to
        if wrt and wrt.rel and wrt.rel.to._meta == opts:
            func = getattr(manipulator.original_object, 'get_%s_list' %
                    related.get_method_name_part())
            orig_list = func()
            form.order_objects.extend(orig_list)

    c = Context(request, {
        'title': _('Change %s') % opts.verbose_name,
        'form': form,
        'object_id': object_id,
        'original': manipulator.original_object,
        'is_popup': request.REQUEST.has_key('_popup'),
        'path': path ,
    })
    return render_change_form(model, manipulator, app_label, c, change=True)
