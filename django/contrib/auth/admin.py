from django.contrib.auth.forms import UserCreationForm
from django.contrib.auth.models import User, Group
from django.core.exceptions import PermissionDenied
from django import oldforms, template
from django.shortcuts import render_to_response
from django.http import HttpResponseRedirect
from django.utils.translation import ugettext, ugettext_lazy as _
from django.contrib import admin

class GroupAdmin(admin.ModelAdmin):
    search_fields = ('name',)
    filter_horizontal = ('permissions',)

class UserAdmin(admin.ModelAdmin):
    fieldsets = (
        (None, {'fields': ('username', 'password')}),
        (_('Personal info'), {'fields': ('first_name', 'last_name', 'email')}),
        (_('Permissions'), {'fields': ('is_staff', 'is_active', 'is_superuser', 'user_permissions')}),
        (_('Important dates'), {'fields': ('last_login', 'date_joined')}),
        (_('Groups'), {'fields': ('groups',)}),
    )
    list_display = ('username', 'email', 'first_name', 'last_name', 'is_staff')
    list_filter = ('is_staff', 'is_superuser')
    search_fields = ('username', 'first_name', 'last_name', 'email')
    filter_horizontal = ('user_permissions',)

    def add_view(self, request):
        if not self.has_change_permission(request):
            raise PermissionDenied
        manipulator = UserCreationForm()
        if request.method == 'POST':
            new_data = request.POST.copy()
            errors = manipulator.get_validation_errors(new_data)
            if not errors:
                new_user = manipulator.save(new_data)
                msg = _('The %(name)s "%(obj)s" was added successfully.') % {'name': 'user', 'obj': new_user}
                if "_addanother" in request.POST:
                    request.user.message_set.create(message=msg)
                    return HttpResponseRedirect(request.path)
                else:
                    request.user.message_set.create(message=msg + ' ' + ugettext("You may edit it again below."))
                    return HttpResponseRedirect('../%s/' % new_user.id)
        else:
            errors = new_data = {}
        form = oldforms.FormWrapper(manipulator, new_data, errors)
        return render_to_response('admin/auth/user/add_form.html', {
            'title': _('Add user'),
            'form': form,
            'is_popup': '_popup' in request.REQUEST,
            'add': True,
            'change': False,
            'has_add_permission': True,
            'has_delete_permission': False,
            'has_change_permission': True,
            'has_file_field': False,
            'has_absolute_url': False,
            'auto_populated_fields': (),
            'opts': User._meta,
            'username_help_text': User._meta.get_field('username').help_text,
        }, context_instance=template.RequestContext(request))

admin.site.register(Group, GroupAdmin)
admin.site.register(User, UserAdmin)

