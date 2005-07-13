from django.core import meta

__all__ = ['auth', 'comments', 'core']

# Alter this package's __path__ variable so that calling code can import models
# from "django.models" even though the model code doesn't physically live
# within django.models.
for mod in meta.get_installed_models():
    __path__.extend(mod.__path__)

# First, import all models so the metaclasses run.
modules = meta.get_installed_model_modules(__all__)

# Now, create the extra methods that we couldn't create earlier because
# relationships hadn't been known until now.
for mod in modules:
    for klass in mod._MODELS:

        # Add "get_thingie", "get_thingie_count" and "get_thingie_list" methods
        # for all related objects.
        for rel_obj, rel_field in klass._meta.get_all_related_objects():
            # Determine whether this related object is in another app.
            # If it's in another app, the method names will have the app
            # label prepended, and the add_BLAH() method will not be
            # generated.
            rel_mod = rel_obj.get_model_module()
            rel_obj_name = klass._meta.get_rel_object_method_name(rel_obj, rel_field)
            if isinstance(rel_field.rel, meta.OneToOne):
                # Add "get_thingie" methods for one-to-one related objects.
                # EXAMPLE: Place.get_restaurants_restaurant()
                func = meta.curry(meta.method_get_related, 'get_object', rel_mod, rel_field)
                func.__doc__ = "Returns the associated `%s.%s` object." % (rel_obj.app_label, rel_obj.module_name)
                setattr(klass, 'get_%s' % rel_obj_name, func)
            elif isinstance(rel_field.rel, meta.ManyToOne):
                # Add "get_thingie" methods for many-to-one related objects.
                # EXAMPLE: Poll.get_choice()
                func = meta.curry(meta.method_get_related, 'get_object', rel_mod, rel_field)
                func.__doc__ = "Returns the associated `%s.%s` object matching the given criteria." % (rel_obj.app_label, rel_obj.module_name)
                setattr(klass, 'get_%s' % rel_obj_name, func)
                # Add "get_thingie_count" methods for many-to-one related objects.
                # EXAMPLE: Poll.get_choice_count()
                func = meta.curry(meta.method_get_related, 'get_count', rel_mod, rel_field)
                func.__doc__ = "Returns the number of associated `%s.%s` objects." % (rel_obj.app_label, rel_obj.module_name)
                setattr(klass, 'get_%s_count' % rel_obj_name, func)
                # Add "get_thingie_list" methods for many-to-one related objects.
                # EXAMPLE: Poll.get_choice_list()
                func = meta.curry(meta.method_get_related, 'get_list', rel_mod, rel_field)
                func.__doc__ = "Returns a list of associated `%s.%s` objects." % (rel_obj.app_label, rel_obj.module_name)
                setattr(klass, 'get_%s_list' % rel_obj_name, func)
                # Add "add_thingie" methods for many-to-one related objects,
                # but only for related objects that are in the same app.
                # EXAMPLE: Poll.add_choice()
                if rel_obj.app_label == klass._meta.app_label:
                    func = meta.curry(meta.method_add_related, rel_obj, rel_mod, rel_field)
                    func.alters_data = True
                    setattr(klass, 'add_%s' % rel_obj_name, func)
                del func
            del rel_obj_name, rel_mod, rel_obj, rel_field # clean up

        # Do the same for all related many-to-many objects.
        for rel_opts, rel_field in klass._meta.get_all_related_many_to_many_objects():
            rel_mod = rel_opts.get_model_module()
            rel_obj_name = klass._meta.get_rel_object_method_name(rel_opts, rel_field)
            setattr(klass, 'get_%s' % rel_obj_name, meta.curry(meta.method_get_related_many_to_many, 'get_object', rel_mod, rel_field))
            setattr(klass, 'get_%s_count' % rel_obj_name, meta.curry(meta.method_get_related_many_to_many, 'get_count', rel_mod, rel_field))
            setattr(klass, 'get_%s_list' % rel_obj_name, meta.curry(meta.method_get_related_many_to_many, 'get_list', rel_mod, rel_field))
            if rel_opts.app_label == klass._meta.app_label:
                func = meta.curry(meta.method_set_related_many_to_many, rel_opts, rel_field)
                func.alters_data = True
                setattr(klass, 'set_%s' % rel_opts.module_name, func)
                del func
            del rel_obj_name, rel_mod, rel_opts, rel_field # clean up

        # Add "set_thingie_order" and "get_thingie_order" methods for objects
        # that are ordered with respect to this.
        for obj in klass._meta.get_ordered_objects():
            func = meta.curry(meta.method_set_order, obj)
            func.__doc__ = "Sets the order of associated `%s.%s` objects to the given ID list." % (obj.app_label, obj.module_name)
            func.alters_data = True
            setattr(klass, 'set_%s_order' % obj.object_name.lower(), func)

            func = meta.curry(meta.method_get_order, obj)
            func.__doc__ = "Returns the order of associated `%s.%s` objects as a list of IDs." % (obj.app_label, obj.module_name)
            setattr(klass, 'get_%s_order' % obj.object_name.lower(), func)
            del func, obj # clean up
        del klass # clean up
    del mod
del modules

# Expose get_app and get_module.
from django.core.meta import get_app, get_module
