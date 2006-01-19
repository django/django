from django import forms, template
from django.conf import settings
from django.contrib.admin.views.decorators import staff_member_required
from django.core.exceptions import ImproperlyConfigured, ObjectDoesNotExist, PermissionDenied
from django.shortcuts import get_object_or_404, render_to_response
from django.db import models
from django.db.models.fields import BoundField, BoundFieldLine, BoundFieldSet
from django.http import Http404, HttpResponse, HttpResponseRedirect
from django.template import loader
from django.utils import dateformat
from django.utils.html import escape
from django.utils.text import capfirst, get_text_list
import operator
from itertools import izip

try:
    from django.contrib.admin.models import LogEntry, ADDITION, CHANGE, DELETION
except ImportError:
    raise ImproperlyConfigured, "You don't have 'django.contrib.admin' in INSTALLED_APPS."

ADMIN_PREFIX = "/admin/"

use_raw_id_admin = lambda field: isinstance(field.rel, (models.ManyToOne, models.ManyToMany)) and field.rel.raw_id_admin

def matches_app(mod, comps):
    modcomps = mod.__name__.split('.')[:-1] #HACK: leave off 'models'
    for c, mc in izip(comps, modcomps):
        if c != mc:
            return [], False
    return comps[len(modcomps):], True

def find_model(mod, remaining):
    if len(remaining) == 0:
        raise Http404
    if len(remaining) == 1:
        if hasattr(mod, '_MODELS'):
            name = remaining[0]
            for model in mod._MODELS:
                if model.__name__.lower() == name:
                    return model
            raise Http404
        else:
            raise Http404
    else:
        child = getattr(mod, remaining[0], None)
        if child:
            return find_model(child, remaining[1:])
        else:
            raise Http404

def get_app_label(mod):
    #HACK
    return mod.__name__.split('.')[-2]

def get_model_and_app(path):
    comps = path.split('/')
    comps = comps[:-1] # remove '' after final /
    for mod in models.get_installed_models():
        remaining, matched = matches_app(mod, comps)
        if matched and len(remaining) > 0:
            return (find_model(mod, remaining), get_app_label(mod))
    raise Http404 # Couldn't find app

_model_urls = {}

def url_for_model(model):
    try:
        return _model_urls[model]
    except KeyError:
        comps = model.__module__.split('.')
        for mod in models.get_installed_models():
            remaining, matched =  matches_app(mod, comps)
            if matched and len(remaining) > 0:
                comps = comps[:-len(remaining)] + remaining[1:]
                url = "%s%s/%s/" % (ADMIN_PREFIX, '/'.join(comps) , model.__name__.lower())
                _model_urls[model] = url
                return url
        raise ImproperlyConfigured, '%s is not a model in an installed app' % model.__name__

def log_add_message(user, opts, manipulator, new_object):
    pk_value = getattr(new_object, opts.pk.attname)
    LogEntry.objects.log_action(user.id, opts.get_content_type_id(), pk_value, str(new_object), ADDITION)

def get_javascript_imports(opts, auto_populated_fields, ordered_objects, field_sets):
# Put in any necessary JavaScript imports.
    js = ['js/core.js', 'js/admin/RelatedObjectLookups.js']
    if auto_populated_fields:
        js.append('js/urlify.js')
    if opts.has_field_type(models.DateTimeField) or opts.has_field_type(models.TimeField) or opts.has_field_type(models.DateField):
        js.extend(['js/calendar.js', 'js/admin/DateTimeShortcuts.js'])
    if ordered_objects:
        js.extend(['js/getElementsBySelector.js', 'js/dom-drag.js' , 'js/admin/ordering.js'])
    if opts.admin.js:
        js.extend(opts.admin.js)
    seen_collapse = False
    for field_set in field_sets:
        if not seen_collapse and 'collapse' in field_set.classes:
            seen_collapse = True
            js.append('js/admin/CollapsedFieldsets.js')

        for field_line in field_set:
            try:
                for f in field_line:
                    if f.rel and isinstance(f, models.ManyToManyField) and f.rel.filter_interface:
                        js.extend(['js/SelectBox.js' , 'js/SelectFilter2.js'])
                        raise StopIteration
            except StopIteration:
                break
    return js

class AdminBoundField(BoundField):
    def __init__(self, field, field_mapping, original):
        super(AdminBoundField, self).__init__(field, field_mapping, original)

        self.element_id = self.form_fields[0].get_id()
        self.has_label_first = not isinstance(self.field, models.BooleanField)
        self.raw_id_admin = use_raw_id_admin(field)
        self.is_date_time = isinstance(field, models.DateTimeField)
        self.is_file_field = isinstance(field, models.FileField)
        self.needs_add_label = field.rel and isinstance(field.rel, models.ManyToOne) or isinstance(field.rel, models.ManyToMany) and field.rel.to._meta.admin
        self.hidden = isinstance(self.field, models.AutoField)
        self.first = False

        classes = []
        if self.raw_id_admin:
            classes.append('nowrap')
        if max([bool(f.errors()) for f in self.form_fields]):
            classes.append('error')
        if classes:
            self.cell_class_attribute = ' class="%s" ' % ' '.join(classes)
        self._repr_filled = False

        if field.rel:
            self.related_url = url_for_model(field.rel.to)

    def existing_display(self):
        try:
            return self._display
        except AttributeError:
            if isinstance(self.field.rel, models.ManyToOne):
                self._display = getattr(self.original, 'get_%s' % self.field.name)()
            elif isinstance(self.field.rel, models.ManyToMany):
                self._display = ", ".join([str(obj) for obj in getattr(self.original, 'get_%s_list' % self.field.rel.singular)()])
            return self._display

    def __repr__(self):
        return repr(self.__dict__)

    def html_error_list(self):
        return " ".join([form_field.html_error_list() for form_field in self.form_fields if form_field.errors])

    def original_url(self):
        if self.is_file_field and self.original and self.field.attname:
            url_method = getattr(self.original, 'get_%s_url' % self.field.attname)
            if callable(url_method):
                return url_method()
        return ''

class AdminBoundFieldLine(BoundFieldLine):
    def __init__(self, field_line, field_mapping, original):
        super(AdminBoundFieldLine, self).__init__(field_line, field_mapping, original, AdminBoundField)
        for bound_field in self:
            bound_field.first = True
            break

class AdminBoundFieldSet(BoundFieldSet):
    def __init__(self, field_set, field_mapping, original):
        super(AdminBoundFieldSet, self).__init__(field_set, field_mapping, original, AdminBoundFieldLine)

class BoundManipulator(object):
    def __init__(self, model, manipulator, field_mapping):
        self.model = model
        self.opts = model._meta
        self.inline_related_objects = self.opts.get_followed_related_objects(manipulator.follow)
        self.original = getattr(manipulator, 'original_object', None)
        self.bound_field_sets = [field_set.bind(field_mapping, self.original, AdminBoundFieldSet)
                                 for field_set in self.opts.admin.get_field_sets(self.opts)]
        self.ordered_objects = self.opts.get_ordered_objects()[:]

class AdminBoundManipulator(BoundManipulator):
    def __init__(self, model, manipulator, field_mapping):
        super(AdminBoundManipulator, self).__init__(model, manipulator, field_mapping)
        field_sets = self.opts.admin.get_field_sets(self.opts)

        self.auto_populated_fields = [f for f in self.opts.fields if f.prepopulate_from]
        self.javascript_imports = get_javascript_imports(self.opts, self.auto_populated_fields, self.ordered_objects, field_sets);

        self.coltype = self.ordered_objects and 'colMS' or 'colM'
        self.has_absolute_url = hasattr(model, 'get_absolute_url')
        self.form_enc_attrib = self.opts.has_field_type(models.FileField) and 'enctype="multipart/form-data" ' or ''

        self.first_form_field_id = self.bound_field_sets[0].bound_field_lines[0].bound_fields[0].form_fields[0].get_id();
        self.ordered_object_pk_names = [o.pk.name for o in self.ordered_objects]

        opts = self.opts
        self.save_on_top = opts.admin.save_on_top
        self.save_as = opts.admin.save_as

        self.content_type_id = opts.get_content_type_id()
        self.verbose_name_plural = opts.verbose_name_plural
        self.verbose_name = opts.verbose_name
        self.object_name = opts.object_name

    def get_ordered_object_pk(self, ordered_obj):
        for name in self.ordered_object_pk_names:
            if hasattr(ordered_obj, name):
                return str(getattr(ordered_obj, name))
        return ""

def render_change_form(model, manipulator, app_label, context, add=False, change=False, show_delete=False, form_url=''):
    opts = model._meta
    extra_context = {
        'add': add,
        'change': change,
        'bound_manipulator': AdminBoundManipulator(model, manipulator, context['form']),
        'has_delete_permission': context['perms'][app_label][opts.get_delete_permission()],
        'form_url': form_url,
        'app_label': app_label,
    }
    context.update(extra_context)
    return render_to_response(["admin/%s/%s/change_form" % (app_label, opts.object_name.lower() ),
                               "admin/%s/change_form" % app_label ,
                               "admin/change_form"], context_instance=context)

def index(request):
    return render_to_response('admin/index', {'title': _('Site administration')}, context_instance=template.RequestContext(request))
index = staff_member_required(index)

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
    form = forms.FormWrapper(manipulator, new_data, errors)

    c = template.RequestContext(request, {
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
    form = forms.FormWrapper(manipulator, new_data, errors)
    form.original = manipulator.original_object
    form.order_objects = []

    c = template.RequestContext(request, {
        'title': _('Change %s') % opts.verbose_name,
        'form': form,
        'object_id': object_id,
        'original': manipulator.original_object,
        'is_popup': request.REQUEST.has_key('_popup'),
        'path': path,
    })
    return render_change_form(model, manipulator, app_label, c, change=True)
change_stage = staff_member_required(change_stage)

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
                    nh(deleted_objects, current_depth, ['%s: <a href="../../../../%s/%s/%s/change/">%s</a>' % \
                        (capfirst(related.opts.verbose_name), related.opts.app_label, related.opts.object_name.lower(),
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
                    nh(deleted_objects, current_depth, ['%s: <a href="../../../../%s/%s/%s/change/">%s</a>' % \
                        (capfirst(related.opts.verbose_name), related.opts.app_label, related.opts.object_name.lower(), getattr(sub_obj, related.opts.pk.attname), escape(str(sub_obj))), []])
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
    }, context_instance=template.RequestContext(request))
delete_stage = staff_member_required(delete_stage)

def history(request, app_label, module_name, object_id):
    action_list = LogEntry.objects.get_list(object_id__exact=object_id, content_type__id__exact=opts.get_content_type_id(),
        order_by=("action_time",), select_related=True)
    # If no history was found, see whether this object even exists.
    obj = get_object_or_404(mod, pk=object_id)
    return render_to_response('admin/object_history', {
        'title': _('Change history: %s') % obj,
        'action_list': action_list,
        'module_name': capfirst(opts.verbose_name_plural),
        'object': obj,
    }, context_instance=template.RequestContext(request))
history = staff_member_required(history)
