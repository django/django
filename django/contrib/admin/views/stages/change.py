from django.contrib.admin.views.main import get_model_and_app
from django.core import formfields, template
from django.http import Http404
from django.core.exceptions import ImproperlyConfigured, ObjectDoesNotExist, PermissionDenied
from django.core.extensions import DjangoContext as Context
from django.contrib.admin.views.stages.modify import render_change_form
from django.db import models
from django.utils.text import capfirst, get_text_list
from django.http import HttpResponse, HttpResponseRedirect
from django.contrib.admin.views.decorators import staff_member_required
try:
    from django.contrib.admin.models import LogEntry, ADDITION, CHANGE, DELETION
except ImportError:
    raise ImproperlyConfigured, "You don't have 'django.contrib.admin' in INSTALLED_APPS."

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

        #save a copy of the data to use for errors later.
        data = new_data.copy()
        manipulator.do_html2python(new_data)
        #update the manipulator with the effects of previous commands.
        manipulator.update(new_data)
        #get the errors on the updated shape of the manipulator
        #HACK - validators should not work on POSTED data directly...

        if request.POST.has_key("_preview"):
            errors = manipulator.get_validation_errors(data)
        elif request.POST.has_key("command"):
            command_name = request.POST.get("command")
            manipulator.do_command(command_name)
            errors = manipulator.get_validation_errors(data)
            new_data = manipulator.flatten_data()
        else:
            errors = manipulator.get_validation_errors(data)
            if errors:
                new_data = manipulator.flatten_data()
            else:
                new_object = manipulator.save_from_update()
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
        errors = {}

    # Populate the FormWrapper.
    form = formfields.FormWrapper(manipulator, new_data, errors)
    form.original = manipulator.original_object
    form.order_objects = []

    c = Context(request, {
        'title': _('Change %s') % opts.verbose_name,
        'form': form,
        'object_id': object_id,
        'original': manipulator.original_object,
        'is_popup': request.REQUEST.has_key('_popup'),
        'path': path ,
    })
    return render_change_form(model, manipulator, app_label, c, change=True)
change_stage = staff_member_required(change_stage)
