# Generic admin views.
from django.contrib.admin.views.decorators import staff_member_required
from django.contrib.admin.filterspecs import FilterSpec
from django.core import formfields, meta, template
from django.core.template import loader
from django.core.meta.fields import BoundField, BoundFieldLine, BoundFieldSet
from django.core.exceptions import Http404, ImproperlyConfigured, ObjectDoesNotExist, PermissionDenied
from django.core.extensions import DjangoContext as Context
from django.core.extensions import get_object_or_404, render_to_response
from django.core.paginator import ObjectPaginator, InvalidPage
from django.conf.settings import ADMIN_MEDIA_PREFIX
try:
    from django.models.admin import log
except ImportError:
    raise ImproperlyConfigured, "You don't have 'django.contrib.admin' in INSTALLED_APPS."
from django.utils.html import escape
from django.utils.httpwrappers import HttpResponse, HttpResponseRedirect
from django.utils.text import capfirst, get_text_list
from django.utils import dateformat
from django.utils.dates import MONTHS
from django.utils.html import escape
import operator

# The system will display a "Show all" link only if the total result count
# is less than or equal to this setting.
MAX_SHOW_ALL_ALLOWED = 200

DEFAULT_RESULTS_PER_PAGE = 100

ALL_VAR = 'all'
ORDER_VAR = 'o'
ORDER_TYPE_VAR = 'ot'
PAGE_VAR = 'p'
SEARCH_VAR = 'q'
IS_POPUP_VAR = 'pop'

# Text to display within changelist table cells if the value is blank.
EMPTY_CHANGELIST_VALUE = '(None)'

def _get_mod_opts(app_label, module_name):
    "Helper function that returns a tuple of (module, opts), raising Http404 if necessary."
    try:
        mod = meta.get_module(app_label, module_name)
    except ImportError:
        raise Http404 # Invalid app or module name. Maybe it's not in INSTALLED_APPS.
    opts = mod.Klass._meta
    if not opts.admin:
        raise Http404 # This object is valid but has no admin interface.
    return mod, opts

def index(request):
    return render_to_response('admin/index', {'title': _('Site administration')}, context_instance=Context(request))
index = staff_member_required(index)

class IncorrectLookupParameters(Exception):
    pass

class ChangeList(object):
    def __init__(self, request, app_label, module_name):
        self.get_modules_and_options(app_label, module_name, request)
        self.get_search_parameters(request)
        self.get_ordering()
        self.query = request.GET.get(SEARCH_VAR, '')
        self.get_lookup_params()
        self.get_results(request)
        self.title = (self.is_popup
                      and _('Select %s') % self.opts.verbose_name
                      or _('Select %s to change') % self.opts.verbose_name)
        self.get_filters(request)
        self.pk_attname = self.lookup_opts.pk.attname

    def get_filters(self, request):
        self.filter_specs = []
        if self.lookup_opts.admin.list_filter and not self.opts.one_to_one_field:
            filter_fields = [self.lookup_opts.get_field(field_name) \
                              for field_name in self.lookup_opts.admin.list_filter]
            for f in filter_fields:
                spec = FilterSpec.create(f, request, self.params)
                if spec and spec.has_output():
                    self.filter_specs.append(spec)
        self.has_filters = bool(self.filter_specs)

    def get_query_string(self, new_params={}, remove=[]):
        p = self.params.copy()
        for r in remove:
            for k in p.keys():
                if k.startswith(r):
                    del p[k]
        for k, v in new_params.items():
            if p.has_key(k) and v is None:
                del p[k]
            elif v is not None:
                p[k] = v
        return '?' + '&amp;'.join(['%s=%s' % (k, v) for k, v in p.items()]).replace(' ', '%20')

    def get_modules_and_options(self, app_label, module_name, request):
        self.mod, self.opts = _get_mod_opts(app_label, module_name)
        if not request.user.has_perm(app_label + '.' + self.opts.get_change_permission()):
            raise PermissionDenied

        self.lookup_mod, self.lookup_opts = self.mod, self.opts

    def get_search_parameters(self, request):
        # Get search parameters from the query string.
        try:
            self.page_num = int(request.GET.get(PAGE_VAR, 0))
        except ValueError:
            self.page_num = 0
        self.show_all = request.GET.has_key(ALL_VAR)
        self.is_popup = request.GET.has_key(IS_POPUP_VAR)
        self.params = dict(request.GET.items())
        if self.params.has_key(PAGE_VAR):
            del self.params[PAGE_VAR]

    def get_results(self, request):
        lookup_mod, lookup_params, show_all, page_num = \
            self.lookup_mod, self.lookup_params, self.show_all, self.page_num
        # Get the results.
        try:
            paginator = ObjectPaginator(lookup_mod, lookup_params, DEFAULT_RESULTS_PER_PAGE)
        # Naked except! Because we don't have any other way of validating "params".
        # They might be invalid if the keyword arguments are incorrect, or if the
        # values are not in the correct type (which would result in a database
        # error).
        except:
            raise IncorrectLookupParameters()

        # Get the total number of objects, with no filters applied.
        real_lookup_params = lookup_params.copy()
        del real_lookup_params['order_by']
        if real_lookup_params:
            full_result_count = lookup_mod.get_count()
        else:
            full_result_count = paginator.hits
        del real_lookup_params
        result_count = paginator.hits
        can_show_all = result_count <= MAX_SHOW_ALL_ALLOWED
        multi_page = result_count > DEFAULT_RESULTS_PER_PAGE

        # Get the list of objects to display on this page.
        if (show_all and can_show_all) or not multi_page:
            result_list = lookup_mod.get_list(**lookup_params)
        else:
            try:
                result_list = paginator.get_page(page_num)
            except InvalidPage:
                result_list = []
        (self.result_count, self.full_result_count, self.result_list,
            self.can_show_all, self.multi_page, self.paginator) = (result_count,
                  full_result_count, result_list, can_show_all, multi_page, paginator )

    def url_for_result(self, result):
        return "%s/" % getattr(result, self.pk_attname)

    def get_ordering(self):
        lookup_opts, params = self.lookup_opts, self.params
        # For ordering, first check the "ordering" parameter in the admin options,
        # then check the object's default ordering. If neither of those exist,
        # order descending by ID by default. Finally, look for manually-specified
        # ordering from the query string.
        ordering = lookup_opts.admin.ordering or lookup_opts.ordering or ['-' + lookup_opts.pk.name]

        # Normalize it to new-style ordering.
        ordering = meta.handle_legacy_orderlist(ordering)

        if ordering[0].startswith('-'):
            order_field, order_type = ordering[0][1:], 'desc'
        else:
            order_field, order_type = ordering[0], 'asc'
        if params.has_key(ORDER_VAR):
            try:
                try:
                    f = lookup_opts.get_field(lookup_opts.admin.list_display[int(params[ORDER_VAR])])
                except meta.FieldDoesNotExist:
                    pass
                else:
                    if not isinstance(f.rel, meta.ManyToOne) or not f.null:
                        order_field = f.name
            except (IndexError, ValueError):
                pass # Invalid ordering specified. Just use the default.
        if params.has_key(ORDER_TYPE_VAR) and params[ORDER_TYPE_VAR] in ('asc', 'desc'):
            order_type = params[ORDER_TYPE_VAR]
        self.order_field, self.order_type = order_field, order_type

    def get_lookup_params(self):
        # Prepare the lookup parameters for the API lookup.
        (params, order_field, lookup_opts, order_type, opts, query) = \
           (self.params, self.order_field, self.lookup_opts, self.order_type, self.opts, self.query)

        lookup_params = params.copy()
        for i in (ALL_VAR, ORDER_VAR, ORDER_TYPE_VAR, SEARCH_VAR, IS_POPUP_VAR):
            if lookup_params.has_key(i):
                del lookup_params[i]
        # If the order-by field is a field with a relationship, order by the value
        # in the related table.
        lookup_order_field = order_field
        try:
            f = lookup_opts.get_field(order_field)
        except meta.FieldDoesNotExist:
            pass
        else:
            if isinstance(lookup_opts.get_field(order_field).rel, meta.ManyToOne):
                f = lookup_opts.get_field(order_field)
                rel_ordering = f.rel.to.ordering and f.rel.to.ordering[0] or f.rel.to.pk.column
                lookup_order_field = '%s.%s' % (f.rel.to.db_table, rel_ordering)
        # Use select_related if one of the list_display options is a field with a
        # relationship.
        if lookup_opts.admin.list_select_related:
            lookup_params['select_related'] = True
        else:
            for field_name in lookup_opts.admin.list_display:
                try:
                    f = lookup_opts.get_field(field_name)
                except meta.FieldDoesNotExist:
                    pass
                else:
                    if isinstance(f.rel, meta.ManyToOne):
                        lookup_params['select_related'] = True
                        break
        lookup_params['order_by'] = ((order_type == 'desc' and '-' or '') + lookup_order_field,)
        if lookup_opts.admin.search_fields and query:
            complex_queries = []
            for bit in query.split():
                or_queries = []
                for field_name in lookup_opts.admin.search_fields:
                    or_queries.append(meta.Q(**{'%s__icontains' % field_name: bit}))
                complex_queries.append(reduce(operator.or_, or_queries))
            lookup_params['complex'] = reduce(operator.and_, complex_queries)
        if opts.one_to_one_field:
            lookup_params.update(opts.one_to_one_field.rel.limit_choices_to)
        self.lookup_params = lookup_params

def change_list(request, app_label, module_name):
    try:
        cl = ChangeList(request, app_label, module_name)
    except IncorrectLookupParameters:
        return HttpResponseRedirect(request.path)

    c = Context(request, {
        'title': cl.title,
        'is_popup': cl.is_popup,
        'cl' : cl
    })
    c.update({'has_add_permission': c['perms'][app_label][cl.opts.get_add_permission()]}),
    return render_to_response(['admin/%s/%s/change_list' % (app_label, cl.opts.object_name.lower()),
                               'admin/%s/change_list' % app_label,
                               'admin/change_list'], context_instance=c)
change_list = staff_member_required(change_list)

use_raw_id_admin = lambda field: isinstance(field.rel, (meta.ManyToOne, meta.ManyToMany)) and field.rel.raw_id_admin

def get_javascript_imports(opts,auto_populated_fields, ordered_objects, field_sets):
# Put in any necessary JavaScript imports.
    js = ['js/core.js', 'js/admin/RelatedObjectLookups.js']
    if auto_populated_fields:
        js.append('js/urlify.js')
    if opts.has_field_type(meta.DateTimeField) or opts.has_field_type(meta.TimeField) or opts.has_field_type(meta.DateField):
        js.extend(['js/calendar.js', 'js/admin/DateTimeShortcuts.js'])
    if ordered_objects:
        js.extend(['js/getElementsBySelector.js', 'js/dom-drag.js' , 'js/admin/ordering.js'])
    if opts.admin.js:
        js.extend(opts.admin.js)
    seen_collapse = False
    for field_set in field_sets:
        if not seen_collapse and 'collapse' in field_set.classes:
            seen_collapse = True
            js.append('js/admin/CollapsedFieldsets.js' )

        for field_line in field_set:
            try:
                for f in field_line:
                    if f.rel and isinstance(f, meta.ManyToManyField) and f.rel.filter_interface:
                        js.extend(['js/SelectBox.js' , 'js/SelectFilter2.js'])
                        raise StopIteration
            except StopIteration:
                break
    return js

class AdminBoundField(BoundField):
    def __init__(self, field, field_mapping, original):
        super(AdminBoundField, self).__init__(field, field_mapping, original)

        self.element_id = self.form_fields[0].get_id()
        self.has_label_first = not isinstance(self.field, meta.BooleanField)
        self.raw_id_admin = use_raw_id_admin(field)
        self.is_date_time = isinstance(field, meta.DateTimeField)
        self.is_file_field = isinstance(field, meta.FileField)
        self.needs_add_label = field.rel and isinstance(field.rel, meta.ManyToOne) or isinstance(field.rel, meta.ManyToMany) and field.rel.to.admin
        self.hidden = isinstance(self.field, meta.AutoField)
        self.first = False

        classes = []
        if self.raw_id_admin:
            classes.append('nowrap')
        if max([bool(f.errors()) for f in self.form_fields]):
            classes.append('error')
        if classes:
            self.cell_class_attribute = ' class="%s" ' % ' '.join(classes)
        self._repr_filled = False

    def _fetch_existing_display(self, func_name):
        class_dict = self.original.__class__.__dict__
        func = class_dict.get(func_name)
        return func(self.original)

    def _fill_existing_display(self):
        if getattr(self, '_display_filled', False):
            return
        # HACK
        if isinstance(self.field.rel, meta.ManyToOne):
             func_name = 'get_%s' % self.field.name
             self._display = self._fetch_existing_display(func_name)
        elif isinstance(self.field.rel, meta.ManyToMany):
            func_name = 'get_%s_list' % self.field.rel.singular
            self._display =  ", ".join([str(obj) for obj in self._fetch_existing_display(func_name)])
        self._display_filled = True

    def existing_display(self):
        self._fill_existing_display()
        return self._display

    def __repr__(self):
        return repr(self.__dict__)

    def html_error_list(self):
        return " ".join([form_field.html_error_list() for form_field in self.form_fields if form_field.errors])

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
    def __init__(self, opts, manipulator, field_mapping):
        self.inline_related_objects = opts.get_followed_related_objects(manipulator.follow)
        self.original = hasattr(manipulator, 'original_object') and manipulator.original_object or None
        self.bound_field_sets = [field_set.bind(field_mapping, self.original, AdminBoundFieldSet)
                                 for field_set in opts.admin.get_field_sets(opts)]
        self.ordered_objects = opts.get_ordered_objects()[:]

class AdminBoundManipulator(BoundManipulator):
    def __init__(self, opts, manipulator, field_mapping):
        super(AdminBoundManipulator, self).__init__(opts, manipulator, field_mapping)
        field_sets = opts.admin.get_field_sets(opts)

        self.auto_populated_fields = [f for f in opts.fields if f.prepopulate_from]
        self.javascript_imports = get_javascript_imports(opts, self.auto_populated_fields, self.ordered_objects, field_sets);

        self.coltype = self.ordered_objects and 'colMS' or 'colM'
        self.has_absolute_url = hasattr(opts.get_model_module().Klass, 'get_absolute_url')
        self.form_enc_attrib = opts.has_field_type(meta.FileField) and \
                                'enctype="multipart/form-data" ' or ''

        self.first_form_field_id = self.bound_field_sets[0].bound_field_lines[0].bound_fields[0].form_fields[0].get_id();
        self.ordered_object_pk_names = [o.pk.name for o in self.ordered_objects]

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

def render_change_form(opts, manipulator, app_label, context, add=False, change=False, show_delete=False, form_url=''):
    extra_context = {
        'add': add,
        'change': change,
        'bound_manipulator': AdminBoundManipulator(opts, manipulator, context['form']),
        'has_delete_permission': context['perms'][app_label][opts.get_delete_permission()],
        'form_url': form_url,
        'app_label': app_label,
    }
    context.update(extra_context)
    return render_to_response(["admin/%s/%s/change_form" % (app_label, opts.object_name.lower() ),
                               "admin/%s/change_form" % app_label ,
                               "admin/change_form"], context_instance=context)

def log_add_message(user, opts,manipulator,new_object):
    pk_value = getattr(new_object, opts.pk.attname)
    log.log_action(user.id, opts.get_content_type_id(), pk_value, str(new_object), log.ADDITION)

def add_stage(request, app_label, module_name, show_delete=False, form_url='', post_url='../', post_url_continue='../%s/', object_id_override=None):
    mod, opts = _get_mod_opts(app_label, module_name)
    if not request.user.has_perm(app_label + '.' + opts.get_add_permission()):
        raise PermissionDenied
    manipulator = mod.AddManipulator()
    if request.POST:
        new_data = request.POST.copy()
        if opts.has_field_type(meta.FileField):
            new_data.update(request.FILES)
        errors = manipulator.get_validation_errors(new_data)
        manipulator.do_html2python(new_data)

        if not errors and not request.POST.has_key("_preview"):
            new_object = manipulator.save(new_data)
            log_add_message(request.user, opts,manipulator,new_object)
            msg = _('The %(name)s "%(obj)s" was added successfully.') % {'name':opts.verbose_name, 'obj':new_object}
            pk_value = getattr(new_object,opts.pk.attname)
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
    form = formfields.FormWrapper(manipulator, new_data, errors, edit_inline=True)

    c = Context(request, {
        'title': _('Add %s') % opts.verbose_name,
        'form': form,
        'is_popup': request.REQUEST.has_key('_popup'),
        'show_delete': show_delete,
    })
    if object_id_override is not None:
        c['object_id'] = object_id_override

    return render_change_form(opts, manipulator, app_label, c, add=True)
add_stage = staff_member_required(add_stage)

def log_change_message(user, opts,manipulator,new_object):
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
    log.log_action(user.id, opts.get_content_type_id(), pk_value, str(new_object), log.CHANGE, change_message)

def change_stage(request, app_label, module_name, object_id):
    mod, opts = _get_mod_opts(app_label, module_name)
    if not request.user.has_perm(app_label + '.' + opts.get_change_permission()):
        raise PermissionDenied
    if request.POST and request.POST.has_key("_saveasnew"):
        return add_stage(request, app_label, module_name, form_url='../add/')
    try:
        manipulator = mod.ChangeManipulator(object_id)
    except ObjectDoesNotExist:
        raise Http404

    if request.POST:
        new_data = request.POST.copy()
        if opts.has_field_type(meta.FileField):
            new_data.update(request.FILES)

        errors = manipulator.get_validation_errors(new_data)

        manipulator.do_html2python(new_data)
        if not errors and not request.POST.has_key("_preview"):
            new_object = manipulator.save(new_data)
            log_change_message(request.user,opts,manipulator,new_object)
            msg = _('The %(name)s "%(obj)s" was changed successfully.') % {'name': opts.verbose_name, 'obj':new_object}
            pk_value = getattr(new_object,opts.pk.attname)
            if request.POST.has_key("_continue"):
                request.user.add_message(msg + ' ' + _("You may edit it again below."))
                if request.REQUEST.has_key('_popup'):
                    return HttpResponseRedirect(request.path + "?_popup=1")
                else:
                    return HttpResponseRedirect(request.path)
            elif request.POST.has_key("_saveasnew"):
                request.user.add_message(_('The %(name)s "%(obj)s" was added successfully. You may edit it again below.') % {'name': opts.verbose_name, 'obj': new_object})
                return HttpResponseRedirect("../%s/" % pk_value)
            elif request.POST.has_key("_addanother"):
                request.user.add_message(msg + ' ' + (_("You may add another %s below.") % opts.verbose_name))
                return HttpResponseRedirect("../add/")
            else:
                request.user.add_message(msg)
                return HttpResponseRedirect("../")
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
        if wrt and wrt.rel and wrt.rel.to == opts:
            func = getattr(manipulator.original_object, 'get_%s_list' %
                    related.get_method_name_part())
            orig_list = func()
            form.order_objects.extend(orig_list)

    c = Context(request, {
        'title': _('Change %s') % opts.verbose_name,
        'form': form,
        'object_id': object_id,
        'original': manipulator.original_object,
        'is_popup' : request.REQUEST.has_key('_popup')
    })

    return render_change_form(opts,manipulator, app_label, c, change=True)
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
        if isinstance(related.field.rel, meta.OneToOne):
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

def delete_stage(request, app_label, module_name, object_id):
    import sets
    mod, opts = _get_mod_opts(app_label, module_name)
    if not request.user.has_perm(app_label + '.' + opts.get_delete_permission()):
        raise PermissionDenied
    obj = get_object_or_404(mod, pk=object_id)

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
        log.log_action(request.user.id, opts.get_content_type_id(), object_id, obj_display, log.DELETION)
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

def history(request, app_label, module_name, object_id):
    mod, opts = _get_mod_opts(app_label, module_name)
    action_list = log.get_list(object_id__exact=object_id, content_type__id__exact=opts.get_content_type_id(),
        order_by=("action_time",), select_related=True)
    # If no history was found, see whether this object even exists.
    obj = get_object_or_404(mod, pk=object_id)
    return render_to_response('admin/object_history', {
        'title': _('Change history: %s') % obj,
        'action_list': action_list,
        'module_name': capfirst(opts.verbose_name_plural),
        'object': obj,
    }, context_instance=Context(request))
history = staff_member_required(history)
