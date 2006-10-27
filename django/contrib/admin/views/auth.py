from django.contrib.admin.views.decorators import staff_member_required
from django.contrib.auth.forms import UserCreationForm
from django.contrib.auth.models import User
from django.core.exceptions import PermissionDenied
from django import forms, template
from django.shortcuts import render_to_response
from django.http import HttpResponseRedirect

def user_add_stage(request):
    if not request.user.has_perm('auth.change_user'):
        raise PermissionDenied
    manipulator = UserCreationForm()
    if request.method == 'POST':
        new_data = request.POST.copy()
        errors = manipulator.get_validation_errors(new_data)
        if not errors:
            new_user = manipulator.save(new_data)
            msg = _('The %(name)s "%(obj)s" was added successfully.') % {'name': 'user', 'obj': new_user}
            if request.POST.has_key("_addanother"):
                request.user.message_set.create(message=msg)
                return HttpResponseRedirect(request.path)
            else:
                request.user.message_set.create(message=msg + ' ' + _("You may edit it again below."))
                return HttpResponseRedirect('../%s/' % new_user.id)
    else:
        errors = new_data = {}
    form = forms.FormWrapper(manipulator, new_data, errors)
    return render_to_response('admin/auth/user/add_form.html', {
        'title': _('Add user'),
        'form': form,
        'is_popup': request.REQUEST.has_key('_popup'),
        'add': True,
        'change': False,
        'has_add_permission': True,
        'has_delete_permission': False,
        'has_change_permission': True,
        'has_file_field': False,
        'has_absolute_url': False,
        'auto_populated_fields': (),
        'bound_field_sets': (),
        'first_form_field_id': 'id_username',
        'opts': User._meta,
        'username_help_text': User._meta.get_field('username').help_text,
    }, context_instance=template.RequestContext(request))
user_add_stage = staff_member_required(user_add_stage)
