from django.contrib.admin.models import LogEntry
from django.contrib.admin.views.decorators import staff_member_required
from django.contrib.admin.views.main import get_model_and_app
from django.contrib.admin.views.stages.modify import render_change_form
from django.core import formfields, template
from django.core.exceptions import Http404, ImproperlyConfigured, ObjectDoesNotExist, PermissionDenied
from django.core.extensions import DjangoContext as Context
from django.db import models
from django.http import HttpResponse, HttpResponseRedirect
from django.utils.text import capfirst, get_text_list
try:
    from django.contrib.admin.models import LogEntry, ADDITION, CHANGE, DELETION
except ImportError:
    raise ImproperlyConfigured, "You don't have 'django.contrib.admin' in INSTALLED_APPS."

def log_add_message(user, opts, manipulator, new_object):
    pk_value = getattr(new_object, opts.pk.attname)
    LogEntry.objects.log_action(user.id, opts.get_content_type_id(), pk_value, str(new_object), ADDITION)

def add_stage(request, path, show_delete=False, form_url='', post_url='../', post_url_continue='../%s/change', object_id_override=None):
    model, app_label = get_model_and_app(path)
    opts = model._meta

    if not request.user.has_perm(app_label + '.' + opts.get_add_permission()):
        raise PermissionDenied
    manipulator = model.AddManipulator()
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
        errors = manipulator.get_validation_errors(data)
        if request.POST.has_key("_preview"):
            pass
        elif request.POST.has_key("command"):
            command_name = request.POST.get("command")
            manipulator.do_command(command_name)
            new_data = manipulator.flatten_data()
        elif errors:
            new_data = manipulator.flatten_data()
        else:
            new_object = manipulator.save_from_update()
            log_add_message(request.user, opts, manipulator, new_object)
            msg = _('The %(name)s "%(obj)s" was added successfully.') % {'name': opts.verbose_name, 'obj': new_object}
            pk_value = getattr(new_object, opts.pk.attname)
            # Here, we distinguish between different save types by checking for
            # the presence of keys in request.POST.
            if request.POST.has_key("_continue"):
                request.user.add_message(msg + ' ' + _("You may edit it again below."))
                if request.POST.has_key("_popup"):
                    post_url_continue += "?_popup=1"
                return HttpResponseRedirect(post_url_continue % pk_value)
            if request.POST.has_key("_popup"):
                return HttpResponse('<script type="text/javascript">opener.dismissAddAnotherPopup(window, %s, "%s");</script>' % \
                    (pk_value, repr(new_object).replace('"', '\\"')))
            elif request.POST.has_key("_addanother"):
                request.user.add_message(msg + ' ' + (_("You may add another %s below.") % opts.verbose_name))
                return HttpResponseRedirect(request.path)
            else:
                request.user.add_message(msg)
                return HttpResponseRedirect(post_url)
    else:
        # Add default data.
        new_data = manipulator.flatten_data()

        # Override the defaults with GET params, if they exist.
        new_data.update(dict(request.GET.items()))

        errors = {}

    # Populate the FormWrapper.
    form = formfields.FormWrapper(manipulator, new_data, errors)

    c = Context(request, {
        'title': _('Add %s') % opts.verbose_name,
        'form': form,
        'is_popup': request.REQUEST.has_key('_popup'),
        'show_delete': show_delete,
        'path': path ,
    })

    if object_id_override is not None:
        c['object_id'] = object_id_override

    return render_change_form(model, manipulator, app_label, c, add=True)
add_stage = staff_member_required(add_stage)
