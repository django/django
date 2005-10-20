from django.core import meta

def validate_app(app_label):
    mod = meta.get_app(app_label)
    for klass in mod._MODELS:
        try:
            validate_class(klass)
        except AssertionError, e:
            print e

def validate_class(klass):
    opts = klass._meta
    # Fields.
    for f in opts.fields:
        if isinstance(f, meta.ManyToManyField):
            assert isinstance(f.rel, meta.ManyToMany), \
                  "ManyToManyField %s should have 'rel' set to a ManyToMany instance." % f.name
    # Inline related objects.
    for related in opts.get_followed_related_objects():
        assert len([f for f in related.opts.fields if f.core]) > 0, \
               "At least one field in %s should have core=True, because it's being edited inline by %s." % \
               (related.opts.object_name, opts.object_name)
    # All related objects.
    related_apps_seen = []
    for related in opts.get_all_related_objects():
        if related.opts in related_apps_seen:
            assert related.field.rel.related_name is not None, \
                 "Relationship in field %s.%s needs to set 'related_name' because more than one" \
                 " %s object is referenced in %s." % \
                 (related.opts.object_name, related.field.name, opts.object_name, rel_opts.object_name)
        related_apps_seen.append(related.opts)
    # Etc.
    if opts.admin is not None:
        assert opts.admin.ordering or opts.ordering, \
            "%s needs to set 'ordering' on either its 'admin' or its model," \
            "because it has 'admin' set." % \
            opts.object_name

if __name__ == "__main__":
    import sys
    try:
        validate_app(sys.argv[1])
    except IndexError:
        sys.stderr.write("Usage: %s [appname]\n" % __file__)
        sys.exit(1)
