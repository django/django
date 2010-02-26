from django.core.exceptions import ObjectDoesNotExist
from django.db import models
from django.utils import formats
from django.utils.html import escape
from django.utils.safestring import mark_safe
from django.utils.text import capfirst
from django.utils.encoding import force_unicode, smart_unicode, smart_str
from django.utils.translation import ungettext, ugettext as _
from django.core.urlresolvers import reverse, NoReverseMatch
from django.utils.datastructures import SortedDict

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

def _format_callback(obj, user, admin_site, levels_to_root, perms_needed):
    has_admin = obj.__class__ in admin_site._registry
    opts = obj._meta
    try:
        admin_url = reverse('%s:%s_%s_change'
                            % (admin_site.name,
                               opts.app_label,
                               opts.object_name.lower()),
                            None, (quote(obj._get_pk_val()),))
    except NoReverseMatch:
        admin_url = '%s%s/%s/%s/' % ('../'*levels_to_root,
                                     opts.app_label,
                                     opts.object_name.lower(),
                                     quote(obj._get_pk_val()))
    if has_admin:
        p = '%s.%s' % (opts.app_label,
                       opts.get_delete_permission())
        if not user.has_perm(p):
            perms_needed.add(opts.verbose_name)
        # Display a link to the admin page.
        return mark_safe(u'%s: <a href="%s">%s</a>' %
                         (escape(capfirst(opts.verbose_name)),
                          admin_url,
                          escape(obj)))
    else:
        # Don't display link to edit, because it either has no
        # admin or is edited inline.
        return u'%s: %s' % (capfirst(opts.verbose_name),
                            force_unicode(obj))

def get_deleted_objects(objs, opts, user, admin_site, levels_to_root=4):
    """
    Find all objects related to ``objs`` that should also be
    deleted. ``objs`` should be an iterable of objects.

    Returns a nested list of strings suitable for display in the
    template with the ``unordered_list`` filter.

    `levels_to_root` defines the number of directories (../) to reach
    the admin root path. In a change_view this is 4, in a change_list
    view 2.

    This is for backwards compatibility since the options.delete_selected
    method uses this function also from a change_list view.
    This will not be used if we can reverse the URL.
    """
    collector = NestedObjects()
    for obj in objs:
        # TODO using a private model API!
        obj._collect_sub_objects(collector)

    # TODO This next bit is needed only because GenericRelations are
    # cascade-deleted way down in the internals in
    # DeleteQuery.delete_batch_related, instead of being found by
    # _collect_sub_objects. Refs #12593.
    from django.contrib.contenttypes import generic
    for f in obj._meta.many_to_many:
        if isinstance(f, generic.GenericRelation):
            rel_manager = f.value_from_object(obj)
            for related in rel_manager.all():
                # There's a wierdness here in the case that the
                # generic-related object also has FKs pointing to it
                # from elsewhere. DeleteQuery does not follow those
                # FKs or delete any such objects explicitly (which is
                # probably a bug). Some databases may cascade those
                # deletes themselves, and some won't. So do we report
                # those objects as to-be-deleted? No right answer; for
                # now we opt to report only on objects that Django
                # will explicitly delete, at risk that some further
                # objects will be silently deleted by a
                # referential-integrity-maintaining database.
                collector.add(related.__class__, related.pk, related,
                              obj.__class__, obj)

    perms_needed = set()

    to_delete = collector.nested(_format_callback,
                                 user=user,
                                 admin_site=admin_site,
                                 levels_to_root=levels_to_root,
                                 perms_needed=perms_needed)

    return to_delete, perms_needed


class NestedObjects(object):
    """
    A directed acyclic graph collection that exposes the add() API
    expected by Model._collect_sub_objects and can present its data as
    a nested list of objects.

    """
    def __init__(self):
        # Use object keys of the form (model, pk) because actual model
        # objects may not be unique

        # maps object key to list of child keys
        self.children = SortedDict()

        # maps object key to parent key
        self.parents = SortedDict()

        # maps object key to actual object
        self.seen = SortedDict()

    def add(self, model, pk, obj,
            parent_model=None, parent_obj=None, nullable=False):
        """
        Add item ``obj`` to the graph. Returns True (and does nothing)
        if the item has been seen already.

        The ``parent_obj`` argument must already exist in the graph; if
        not, it's ignored (but ``obj`` is still added with no
        parent). In any case, Model._collect_sub_objects (for whom
        this API exists) will never pass a parent that hasn't already
        been added itself.

        These restrictions in combination ensure the graph will remain
        acyclic (but can have multiple roots).

        ``model``, ``pk``, and ``parent_model`` arguments are ignored
        in favor of the appropriate lookups on ``obj`` and
        ``parent_obj``; unlike CollectedObjects, we can't maintain
        independence from the knowledge that we're operating on model
        instances, and we don't want to allow for inconsistency.

        ``nullable`` arg is ignored: it doesn't affect how the tree of
        collected objects should be nested for display.
        """
        model, pk = type(obj), obj._get_pk_val()

        key = model, pk

        if key in self.seen:
            return True
        self.seen.setdefault(key, obj)

        if parent_obj is not None:
            parent_model, parent_pk = (type(parent_obj),
                                       parent_obj._get_pk_val())
            parent_key = (parent_model, parent_pk)
            if parent_key in self.seen:
                self.children.setdefault(parent_key, list()).append(key)
                self.parents.setdefault(key, parent_key)

    def _nested(self, key, format_callback=None, **kwargs):
        obj = self.seen[key]
        if format_callback:
            ret = [format_callback(obj, **kwargs)]
        else:
            ret = [obj]

        children = []
        for child in self.children.get(key, ()):
            children.extend(self._nested(child, format_callback, **kwargs))
        if children:
            ret.append(children)

        return ret

    def nested(self, format_callback=None, **kwargs):
        """
        Return the graph as a nested list.

        Passes **kwargs back to the format_callback as kwargs.

        """
        roots = []
        for key in self.seen.keys():
            if key not in self.parents:
                roots.extend(self._nested(key, format_callback, **kwargs))
        return roots


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
