from __future__ import unicode_literals

from django.contrib.admin import helpers
from django.contrib.admin.exceptions import DisallowedModelAdminToField
from django.contrib.admin.utils import get_deleted_objects, unquote
from django.core.exceptions import PermissionDenied
from django.db import router
from django.forms.formsets import all_valid
from django.http import Http404
from django.utils.encoding import force_text
from django.utils.html import escape
from django.utils.translation import ugettext as _
from django.views.generic import View

IS_POPUP_VAR = '_popup'
TO_FIELD_VAR = '_to_field'


class AdminCrudView(View):
    admin = None
    object_id = None
    extra_context = None

    def __init__(self, admin, object_id, extra_context, **kwargs):
        super(AdminCrudView, self).__init__(**kwargs)
        self.admin = admin
        self.object_id = object_id
        self.extra_context = extra_context or {}
        self.obj = None

    def _get_object(self, request):
        self.obj = self.obj or self.admin.get_object(request, unquote(self.object_id), self._to_field(request))
        return self.obj

    def _to_field(self, request):
        return request.POST.get(TO_FIELD_VAR, request.GET.get(TO_FIELD_VAR))

    def _check_field_can_be_referenced(self, request):
        to_field = self._to_field(request)
        if to_field and not self.admin.to_field_allowed(request, to_field):
            raise DisallowedModelAdminToField("The field %s cannot be referenced." % to_field)

    def _check_permissions(self, request):
        if not hasattr(self, 'view_action'):
            raise NotImplementedError
        perm = getattr(self.admin, 'has_{}_permission'.format(self.view_action))(request)
        if not perm:
            raise PermissionDenied

    def dispatch(self, request, *args, **kwargs):
        self._check_field_can_be_referenced(request)
        self._check_permissions(request)
        return super(AdminCrudView, self).dispatch(request, *args, **kwargs)


class ChangeFormView(AdminCrudView):
    form_url = ''

    def __init__(self, form_url, **kwargs):
        super(ChangeFormView, self).__init__(**kwargs)
        self.form_url = form_url

    def _get_object(self, request):
        if self.object_id is None:
            return None
        return super(ChangeFormView, self)._get_object(request)

    def _get_form(self, request):
        return self.admin.get_form(request, self._get_object(request))

    def _log_and_response(self):
        raise NotImplementedError

    def post(self, request, *args, **kwargs):
        add = self.object_id is None
        ModelForm = self._get_form(request)
        obj_instance = self._get_object(request) if '_saveasnew' not in request.POST else None
        form = ModelForm(request.POST, request.FILES, instance=obj_instance)
        if form.is_valid():
            form_validated = True
            new_object = self.admin.save_form(request, form, change=True)
        else:
            form_validated = False
            new_object = form.instance
        formsets, inline_instances = self.admin._create_formsets(request, new_object, change=not add)
        if all_valid(formsets) and form_validated:
            return self._log_and_response(request, new_object, form, formsets)

        form_validated = False
        # Hide the "Save" and "Save and continue" buttons if "Save as New" was
        # previously chosen to prevent the interface from getting confusing.
        if "_saveasnew" in request.POST:
            self.extra_context['show_save'] = False
            self.extra_context['show_save_and_continue'] = False
        return self.render_form(
            request, form, form_validated, formsets, inline_instances, initial=None, **kwargs)

    def get_context(self, request, form, form_validated, formsets, inline_instances, initial=None, **kwargs):
        obj = self._get_object(request)
        adminForm = helpers.AdminForm(
            form,
            list(self.admin.get_fieldsets(request, obj)),
            self.admin.get_prepopulated_fields(request, obj),
            self.admin.get_readonly_fields(request, obj),
            model_admin=self.admin)
        media = self.admin.media + adminForm.media
        inline_formsets = self.admin.get_inline_formsets(request, formsets, inline_instances, obj)
        for inline_formset in inline_formsets:
            media = media + inline_formset.media
        context = dict(
            self.admin.admin_site.each_context(request),
            adminform=adminForm,
            object_id=self.object_id,
            original=self._get_object(request),
            is_popup=(IS_POPUP_VAR in request.POST or
                      IS_POPUP_VAR in request.GET),
            to_field=self._to_field(request),
            media=media,
            inline_admin_formsets=inline_formsets,
            errors=helpers.AdminErrorList(form, formsets),
            preserved_filters=self.admin.get_preserved_filters(request),
        )
        context.update(self.extra_context)
        return context

    def render_form(self, request, form, form_validated, formsets, inline_instances,
                    initial=None, **kwargs):
        raise NotImplementedError


class ChangeView(ChangeFormView):
    view_action = 'change'

    def _check_permissions(self, request):
        obj = self._get_object(request)
        perm = getattr(self.admin, 'has_{}_permission'.format(self.view_action))(request, obj)
        if not perm:
            raise PermissionDenied
        if obj is None:
            raise Http404(_('%(name)s object with primary key %(key)r does not exist.') % {
                'name': force_text(self.admin.model._meta.verbose_name), 'key': escape(self.object_id)})

    def get(self, request, **kwargs):
        obj = self._get_object(request)
        form = self._get_form(request)(instance=obj)
        formsets, inline_instances = self.admin._create_formsets(request, obj, change=True)
        form_validated = False
        return self.render_form(
            request, form, form_validated, formsets, inline_instances, initial=None, **kwargs)

    def _log_and_response(self, request, new_object, form, formsets):
        self.admin.save_model(request, new_object, form, True)
        self.admin.save_related(request, form, formsets, True)
        change_message = self.admin.construct_change_message(request, form, formsets, False)
        self.admin.log_change(request, new_object, change_message)
        return self.admin.response_change(request, new_object)

    def get_context(self, request, form, form_validated, formsets, inline_instances, initial=None, **kwargs):
        context = super(ChangeView, self).get_context(
            request, form, form_validated, formsets, inline_instances, initial=initial, **kwargs)
        context.update({
            'title': _('Change %s') % force_text(self.admin.model._meta.verbose_name)
        })
        return context

    def render_form(self, request, form, form_validated, formsets, inline_instances,
                    initial=None, **kwargs):
        context = self.get_context(
            request, form, form_validated, formsets, inline_instances, initial=initial, **kwargs)
        return self.admin.render_change_form(
            request, context, add=False, change=True, form_url=self.form_url, obj=self._get_object(request))


class AddView(ChangeFormView):
    view_action = 'add'
    form_url = ''

    def _log_and_response(self, request, new_object, form, formsets):
        self.admin.save_model(request, new_object, form, False)
        self.admin.save_related(request, form, formsets, False)
        change_message = self.admin.construct_change_message(request, form, formsets, True)
        self.admin.log_addition(request, new_object, change_message)
        return self.admin.response_add(request, new_object)

    def get(self, request, **kwargs):
        initial = self.admin.get_changeform_initial_data(request)
        form = self._get_form(request)(initial=initial)
        formsets, inline_instances = self.admin._create_formsets(request, form.instance, change=False)
        form_validated = False
        return self.render_form(
            request, form, form_validated, formsets, inline_instances, initial=initial, **kwargs)

    def get_context(self, request, form, form_validated, formsets, inline_instances, initial=None, **kwargs):
        context = super(AddView, self).get_context(
            request, form, form_validated, formsets, inline_instances, initial=initial, **kwargs)
        context.update({
            'title': _('Add %s') % force_text(self.admin.model._meta.verbose_name)
        })
        return context

    def render_form(self, request, form, form_validated, formsets, inline_instances,
                    initial=None, **kwargs):
        context = self.get_context(
            request, form, form_validated, formsets, inline_instances, initial=initial, **kwargs)
        return self.admin.render_change_form(
            request, context, add=True, change=False, form_url=self.form_url, obj=self._get_object(request))


class DeleteView(AdminCrudView):
    view_action = 'delete'

    def post(self, request, *args, **kwargs):
        obj = self._get_object(request)
        to_field = self._to_field(request)
        opts = self.admin.model._meta
        using = router.db_for_write(self.admin.model)

        # Populate deleted_objects, a data structure of all related objects that
        # will also be deleted.
        (deleted_objects, model_count, perms_needed, protected) = get_deleted_objects(
            [obj], opts, request.user, self.admin.admin_site, using)

        if request.POST:
            if perms_needed:
                raise PermissionDenied
            obj_display = force_text(obj)
            attr = str(to_field) if to_field else opts.pk.attname
            obj_id = obj.serializable_value(attr)
            self.admin.log_deletion(request, obj, obj_display)
            self.admin.delete_model(request, obj)

            return self.admin.response_delete(request, obj_display, obj_id)
        return self.get(request, *args, **kwargs)

    def get(self, request, *args, **kwargs):
        obj = self._get_object(request)
        to_field = self._to_field(request)
        opts = self.admin.model._meta
        app_label = opts.app_label
        using = router.db_for_write(self.admin.model)

        # Populate deleted_objects, a data structure of all related objects that
        # will also be deleted.
        (deleted_objects, model_count, perms_needed, protected) = get_deleted_objects(
            [obj], opts, request.user, self.admin.admin_site, using)

        object_name = force_text(opts.verbose_name)

        if perms_needed or protected:
            title = _("Cannot delete %(name)s") % {"name": object_name}
        else:
            title = _("Are you sure?")

        context = dict(
            self.admin.admin_site.each_context(request),
            title=title,
            object_name=object_name,
            object=obj,
            deleted_objects=deleted_objects,
            model_count=dict(model_count).items(),
            perms_lacking=perms_needed,
            protected=protected,
            opts=opts,
            app_label=app_label,
            preserved_filters=self.admin.get_preserved_filters(request),
            is_popup=(IS_POPUP_VAR in request.POST or
                      IS_POPUP_VAR in request.GET),
            to_field=to_field,
        )
        context.update(self.extra_context or {})

        return self.admin.render_delete_form(request, context)
