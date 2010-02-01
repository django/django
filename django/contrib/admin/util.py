from django.core.exceptions import ObjectDoesNotExist
from django.db import models
from django.utils import formats
from django.utils.html import escape
from django.utils.safestring import mark_safe
from django.utils.text import capfirst
from django.utils.encoding import force_unicode, smart_unicode, smart_str
from django.utils.translation import ungettext, ugettext as _
from django.core.urlresolvers import reverse, NoReverseMatch


def quote(s):
    """
    Ensure that primary key values do not confuse the admin URLs by escaping
    any '/', '_' and ':' characters. Similar to urllib.quote, except that the
    quoting is slightly different so that it doesn't get automatically
    unquoted by the Web browser.
    """
    if not isinstance(s, basestring):
        return s
    res = list(s)
    for i in range(len(res)):
        c = res[i]
        if c in """:/_#?;@&=+$,"<>%\\""":
            res[i] = '_%02X' % ord(c)
    return ''.join(res)

def unquote(s):
    """
    Undo the effects of quote(). Based heavily on urllib.unquote().
    """
    mychr = chr
    myatoi = int
    list = s.split('_')
    res = [list[0]]
    myappend = res.append
    del list[0]
    for item in list:
        if item[1:2]:
            try:
                myappend(mychr(myatoi(item[:2], 16)) + item[2:])
            except ValueError:
                myappend('_' + item)
        else:
            myappend('_' + item)
    return "".join(res)

def flatten_fieldsets(fieldsets):
    """Returns a list of field names from an admin fieldsets structure."""
    field_names = []
    for name, opts in fieldsets:
        for field in opts['fields']:
            # type checking feels dirty, but it seems like the best way here
            if type(field) == tuple:
                field_names.extend(field)
            else:
                field_names.append(field)
    return field_names

def _nest_help(obj, depth, val):
    current = obj
    for i in range(depth):
        current = current[-1]
    current.append(val)

def get_change_view_url(app_label, module_name, pk, admin_site, levels_to_root):
    """
    Returns the url to the admin change view for the given app_label,
    module_name and primary key.
    """
    try:
        return reverse('%sadmin_%s_%s_change' % (admin_site.name, app_label, module_name), None, (pk,))
    except NoReverseMatch:
        return '%s%s/%s/%s/' % ('../'*levels_to_root, app_label, module_name, pk)

def get_deleted_objects(deleted_objects, perms_needed, user, obj, opts, current_depth, admin_site, levels_to_root=4):
    """
    Helper function that recursively populates deleted_objects.

    `levels_to_root` defines the number of directories (../) to reach the
    admin root path. In a change_view this is 4, in a change_list view 2.

    This is for backwards compatibility since the options.delete_selected
    method uses this function also from a change_list view.
    This will not be used if we can reverse the URL.
    """
    nh = _nest_help # Bind to local variable for performance
    if current_depth > 16:
        return # Avoid recursing too deep.
    opts_seen = []
    for related in opts.get_all_related_objects():
        has_admin = related.model in admin_site._registry
        if related.opts in opts_seen:
            continue
        opts_seen.append(related.opts)
        rel_opts_name = related.get_accessor_name()
        if isinstance(related.field.rel, models.OneToOneRel):
            try:
                sub_obj = getattr(obj, rel_opts_name)
            except ObjectDoesNotExist:
                pass
            else:
                if has_admin:
                    p = '%s.%s' % (related.opts.app_label, related.opts.get_delete_permission())
                    if not user.has_perm(p):
                        perms_needed.add(related.opts.verbose_name)
                        # We don't care about populating deleted_objects now.
                        continue
                if not has_admin:
                    # Don't display link to edit, because it either has no
                    # admin or is edited inline.
                    nh(deleted_objects, current_depth,
                        [u'%s: %s' % (capfirst(related.opts.verbose_name), force_unicode(sub_obj)), []])
                else:
                    # Display a link to the admin page.
                    nh(deleted_objects, current_depth, [mark_safe(u'%s: <a href="%s">%s</a>' %
                        (escape(capfirst(related.opts.verbose_name)),
                        get_change_view_url(related.opts.app_label,
                                            related.opts.object_name.lower(),
                                            sub_obj._get_pk_val(),
                                            admin_site,
                                            levels_to_root),
                        escape(sub_obj))), []])
                get_deleted_objects(deleted_objects, perms_needed, user, sub_obj, related.opts, current_depth+2, admin_site)
        else:
            has_related_objs = False
            for sub_obj in getattr(obj, rel_opts_name).all():
                has_related_objs = True
                if not has_admin:
                    # Don't display link to edit, because it either has no
                    # admin or is edited inline.
                    nh(deleted_objects, current_depth,
                        [u'%s: %s' % (capfirst(related.opts.verbose_name), force_unicode(sub_obj)), []])
                else:
                    # Display a link to the admin page.
                    nh(deleted_objects, current_depth, [mark_safe(u'%s: <a href="%s">%s</a>' %
                        (escape(capfirst(related.opts.verbose_name)),
                        get_change_view_url(related.opts.app_label,
                                            related.opts.object_name.lower(),
                                            sub_obj._get_pk_val(),
                                            admin_site,
                                            levels_to_root),
                        escape(sub_obj))), []])
                get_deleted_objects(deleted_objects, perms_needed, user, sub_obj, related.opts, current_depth+2, admin_site)
            # If there were related objects, and the user doesn't have
            # permission to delete them, add the missing perm to perms_needed.
            if has_admin and has_related_objs:
                p = '%s.%s' % (related.opts.app_label, related.opts.get_delete_permission())
                if not user.has_perm(p):
                    perms_needed.add(related.opts.verbose_name)
    for related in opts.get_all_related_many_to_many_objects():
        has_admin = related.model in admin_site._registry
        if related.opts in opts_seen:
            continue
        opts_seen.append(related.opts)
        rel_opts_name = related.get_accessor_name()
        has_related_objs = False

        # related.get_accessor_name() could return None for symmetrical relationships
        if rel_opts_name:
            rel_objs = getattr(obj, rel_opts_name, None)
            if rel_objs:
                has_related_objs = True

        if has_related_objs:
            for sub_obj in rel_objs.all():
                if not has_admin:
                    # Don't display link to edit, because it either has no
                    # admin or is edited inline.
                    nh(deleted_objects, current_depth, [_('One or more %(fieldname)s in %(name)s: %(obj)s') % \
                        {'fieldname': force_unicode(related.field.verbose_name), 'name': force_unicode(related.opts.verbose_name), 'obj': escape(sub_obj)}, []])
                else:
                    # Display a link to the admin page.
                    nh(deleted_objects, current_depth, [
                        mark_safe((_('One or more %(fieldname)s in %(name)s:') % {'fieldname': escape(force_unicode(related.field.verbose_name)), 'name': escape(force_unicode(related.opts.verbose_name))}) + \
                        (u' <a href="%s">%s</a>' % \
                            (get_change_view_url(related.opts.app_label,
                                                 related.opts.object_name.lower(),
                                                 sub_obj._get_pk_val(),
                                                 admin_site,
                                                 levels_to_root),
                            escape(sub_obj)))), []])
        # If there were related objects, and the user doesn't have
        # permission to change them, add the missing perm to perms_needed.
        if has_admin and has_related_objs:
            p = u'%s.%s' % (related.opts.app_label, related.opts.get_change_permission())
            if not user.has_perm(p):
                perms_needed.add(related.opts.verbose_name)

def model_format_dict(obj):
    """
    Return a `dict` with keys 'verbose_name' and 'verbose_name_plural',
    typically for use with string formatting.

    `obj` may be a `Model` instance, `Model` subclass, or `QuerySet` instance.

    """
    if isinstance(obj, (models.Model, models.base.ModelBase)):
        opts = obj._meta
    elif isinstance(obj, models.query.QuerySet):
        opts = obj.model._meta
    else:
        opts = obj
    return {
        'verbose_name': force_unicode(opts.verbose_name),
        'verbose_name_plural': force_unicode(opts.verbose_name_plural)
    }

def model_ngettext(obj, n=None):
    """
    Return the appropriate `verbose_name` or `verbose_name_plural` value for
    `obj` depending on the count `n`.

    `obj` may be a `Model` instance, `Model` subclass, or `QuerySet` instance.
    If `obj` is a `QuerySet` instance, `n` is optional and the length of the
    `QuerySet` is used.

    """
    if isinstance(obj, models.query.QuerySet):
        if n is None:
            n = obj.count()
        obj = obj.model
    d = model_format_dict(obj)
    singular, plural = d["verbose_name"], d["verbose_name_plural"]
    return ungettext(singular, plural, n or 0)

def lookup_field(name, obj, model_admin=None):
    opts = obj._meta
    try:
        f = opts.get_field(name)
    except models.FieldDoesNotExist:
        # For non-field values, the value is either a method, property or
        # returned via a callable.
        if callable(name):
            attr = name
            value = attr(obj)
        elif (model_admin is not None and hasattr(model_admin, name) and
          not name == '__str__' and not name == '__unicode__'):
            attr = getattr(model_admin, name)
            value = attr(obj)
        else:
            attr = getattr(obj, name)
            if callable(attr):
                value = attr()
            else:
                value = attr
        f = None
    else:
        attr = None
        value = getattr(obj, name)
    return f, attr, value

def label_for_field(name, model, model_admin=None, return_attr=False):
    attr = None
    try:
        label = model._meta.get_field_by_name(name)[0].verbose_name
    except models.FieldDoesNotExist:
        if name == "__unicode__":
            label = force_unicode(model._meta.verbose_name)
        elif name == "__str__":
            label = smart_str(model._meta.verbose_name)
        else:
            if callable(name):
                attr = name
            elif model_admin is not None and hasattr(model_admin, name):
                attr = getattr(model_admin, name)
            elif hasattr(model, name):
                attr = getattr(model, name)
            else:
                message = "Unable to lookup '%s' on %s" % (name, model._meta.object_name)
                if model_admin:
                    message += " or %s" % (model_admin.__name__,)
                raise AttributeError(message)

            if hasattr(attr, "short_description"):
                label = attr.short_description
            elif callable(attr):
                if attr.__name__ == "<lambda>":
                    label = "--"
                else:
                    label = attr.__name__
            else:
                label = name
    if return_attr:
        return (label, attr)
    else:
        return label


def display_for_field(value, field):
    from django.contrib.admin.templatetags.admin_list import _boolean_icon
    from django.contrib.admin.views.main import EMPTY_CHANGELIST_VALUE

    if field.flatchoices:
        return dict(field.flatchoices).get(value, EMPTY_CHANGELIST_VALUE)
    elif value is None:
        return EMPTY_CHANGELIST_VALUE
    elif isinstance(field, models.DateField) or isinstance(field, models.TimeField):
        return formats.localize(value)
    elif isinstance(field, models.BooleanField) or isinstance(field, models.NullBooleanField):
        return _boolean_icon(value)
    elif isinstance(field, models.DecimalField):
        return formats.number_format(value, field.decimal_places)
    elif isinstance(field, models.FloatField):
        return formats.number_format(value)
    else:
        return smart_unicode(value)
