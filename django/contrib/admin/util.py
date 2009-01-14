from django.core.exceptions import ObjectDoesNotExist
from django.db import models
from django.utils.html import escape
from django.utils.safestring import mark_safe
from django.utils.text import capfirst
from django.utils.encoding import force_unicode
from django.utils.translation import ugettext as _

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

def get_deleted_objects(deleted_objects, perms_needed, user, obj, opts, current_depth, admin_site):
    "Helper function that recursively populates deleted_objects."
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
                    nh(deleted_objects, current_depth, [mark_safe(u'%s: <a href="../../../../%s/%s/%s/">%s</a>' %
                        (escape(capfirst(related.opts.verbose_name)),
                        related.opts.app_label,
                        related.opts.object_name.lower(),
                        sub_obj._get_pk_val(),
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
                    nh(deleted_objects, current_depth, [mark_safe(u'%s: <a href="../../../../%s/%s/%s/">%s</a>' % 
                        (escape(capfirst(related.opts.verbose_name)),
                        related.opts.app_label,
                        related.opts.object_name.lower(),
                        sub_obj._get_pk_val(),
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
                        (u' <a href="../../../../%s/%s/%s/">%s</a>' % \
                            (related.opts.app_label, related.opts.module_name, sub_obj._get_pk_val(), escape(sub_obj)))), []])
        # If there were related objects, and the user doesn't have
        # permission to change them, add the missing perm to perms_needed.
        if has_admin and has_related_objs:
            p = u'%s.%s' % (related.opts.app_label, related.opts.get_change_permission())
            if not user.has_perm(p):
                perms_needed.add(related.opts.verbose_name)
