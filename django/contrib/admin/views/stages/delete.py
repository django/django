from django.contrib.admin.views.decorators import staff_member_required
from django.contrib.admin.views.main import get_model_and_app
from django.core.extensions import get_object_or_404,render_to_response
from django.template import RequestContext as Context
from django.utils.text import capfirst
from django.utils.html import escape
from django.db import models
try:
    from django.contrib.admin.models import LogEntry, ADDITION, CHANGE, DELETION
except ImportError:
    raise ImproperlyConfigured, "You don't have 'django.contrib.admin' in INSTALLED_APPS."
from django.http import HttpResponse, HttpResponseRedirect

def _nest_help(obj, depth, val):
    current = obj
    for i in range(depth):
        current = current[-1]
    current.append(val)

def _get_deleted_objects(deleted_objects, perms_needed, user, obj, opts, current_depth):
    "Helper function that recursively populates deleted_objects."
    nh = _nest_help # Bind to local variable for performance
    if current_depth > 16:
        return # Avoid recursing too deep.
    opts_seen = []
    for related in opts.get_all_related_objects():
        if related.opts in opts_seen:
            continue
        opts_seen.append(related.opts)
        rel_opts_name = related.get_method_name_part()
        if isinstance(related.field.rel, models.OneToOne):
            try:
                sub_obj = getattr(obj, 'get_%s' % rel_opts_name)()
            except ObjectDoesNotExist:
                pass
            else:
                if related.opts.admin:
                    p = '%s.%s' % (related.opts.app_label, related.opts.get_delete_permission())
                    if not user.has_perm(p):
                        perms_needed.add(related.opts.verbose_name)
                        # We don't care about populating deleted_objects now.
                        continue
                if related.field.rel.edit_inline or not related.opts.admin:
                    # Don't display link to edit, because it either has no
                    # admin or is edited inline.
                    nh(deleted_objects, current_depth, ['%s: %s' % (capfirst(related.opts.verbose_name), sub_obj), []])
                else:
                    # Display a link to the admin page.
                    nh(deleted_objects, current_depth, ['%s: <a href="../../../../%s/%s/%s/">%s</a>' % \
                        (capfirst(related.opts.verbose_name), related.opts.app_label, related.opts.module_name,
                        getattr(sub_obj, related.opts.pk.attname), sub_obj), []])
                _get_deleted_objects(deleted_objects, perms_needed, user, sub_obj, related.opts, current_depth+2)
        else:
            has_related_objs = False
            for sub_obj in getattr(obj, 'get_%s_list' % rel_opts_name)():
                has_related_objs = True
                if related.field.rel.edit_inline or not related.opts.admin:
                    # Don't display link to edit, because it either has no
                    # admin or is edited inline.
                    nh(deleted_objects, current_depth, ['%s: %s' % (capfirst(related.opts.verbose_name), escape(str(sub_obj))), []])
                else:
                    # Display a link to the admin page.
                    nh(deleted_objects, current_depth, ['%s: <a href="../../../../%s/%s/%s/">%s</a>' % \
                        (capfirst(related.opts.verbose_name), related.opts.app_label, related.opts.module_name, getattr(sub_obj, related.opts.pk.attname), escape(str(sub_obj))), []])
                _get_deleted_objects(deleted_objects, perms_needed, user, sub_obj, related.opts, current_depth+2)
            # If there were related objects, and the user doesn't have
            # permission to delete them, add the missing perm to perms_needed.
            if related.opts.admin and has_related_objs:
                p = '%s.%s' % (related.opts.app_label, related.opts.get_delete_permission())
                if not user.has_perm(p):
                    perms_needed.add(rel_opts.verbose_name)
    for related in opts.get_all_related_many_to_many_objects():
        if related.opts in opts_seen:
            continue
        opts_seen.append(related.opts)
        rel_opts_name = related.get_method_name_part()
        has_related_objs = False
        for sub_obj in getattr(obj, 'get_%s_list' % rel_opts_name)():
            has_related_objs = True
            if related.field.rel.edit_inline or not related.opts.admin:
                # Don't display link to edit, because it either has no
                # admin or is edited inline.
                nh(deleted_objects, current_depth, [_('One or more %(fieldname)s in %(name)s: %(obj)s') % \
                    {'fieldname': related.field.name, 'name': related.opts.verbose_name, 'obj': escape(str(sub_obj))}, []])
            else:
                # Display a link to the admin page.
                nh(deleted_objects, current_depth, [
                    (_('One or more %(fieldname)s in %(name)s:') % {'fieldname': related.field.name, 'name':related.opts.verbose_name}) + \
                    (' <a href="../../../../%s/%s/%s/">%s</a>' % \
                        (related.opts.app_label, related.opts.module_name, getattr(sub_obj, related.opts.pk.attname), escape(str(sub_obj)))), []])
        # If there were related objects, and the user doesn't have
        # permission to change them, add the missing perm to perms_needed.
        if related.opts.admin and has_related_objs:
            p = '%s.%s' % (related.opts.app_label, related.opts.get_change_permission())
            if not user.has_perm(p):
                perms_needed.add(related.opts.verbose_name)

def delete_stage(request, path, object_id):
    import sets
    #mod, opts = _get_mod_opts(app_label, module_name)
    model, app_label = get_model_and_app(path)
    opts = model._meta
    if not request.user.has_perm(app_label + '.' + opts.get_delete_permission()):
        raise PermissionDenied
    obj = get_object_or_404(model, pk=object_id)

    # Populate deleted_objects, a data structure of all related objects that
    # will also be deleted.
    deleted_objects = ['%s: <a href="../../%s/">%s</a>' % (capfirst(opts.verbose_name), object_id, escape(str(obj))), []]
    perms_needed = sets.Set()
    _get_deleted_objects(deleted_objects, perms_needed, request.user, obj, opts, 1)

    if request.POST: # The user has already confirmed the deletion.
        if perms_needed:
            raise PermissionDenied
        obj_display = str(obj)
        obj.delete()
        LogEntry.objects.log_action(request.user.id, opts.get_content_type_id(), object_id, obj_display, DELETION)
        request.user.add_message(_('The %(name)s "%(obj)s" was deleted successfully.') % {'name':opts.verbose_name, 'obj':obj_display})
        return HttpResponseRedirect("../../")
    return render_to_response('admin/delete_confirmation', {
        "title": _("Are you sure?"),
        "object_name": opts.verbose_name,
        "object": obj,
        "deleted_objects": deleted_objects,
        "perms_lacking": perms_needed,
    }, context_instance=Context(request))
delete_stage = staff_member_required(delete_stage)
