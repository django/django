# from django.core import meta
# from django.utils.functional import curry
#
# __all__ = ['auth', 'core']
#
# # Alter this package's __path__ variable so that calling code can import models
# # from "django.models" even though the model code doesn't physically live
# # within django.models.
# for mod in meta.get_installed_models():
#     __path__.extend(mod.__path__)
#
# # First, import all models so the metaclasses run.
# modules = meta.get_installed_model_modules(__all__)
#
# # Now, create the extra methods that we couldn't create earlier because
# # relationships hadn't been known until now.
# for mod in modules:
#     for klass in mod._MODELS:
#
#         # Add "get_thingie", "get_thingie_count" and "get_thingie_list" methods
#         # for all related objects.
#         for related in klass._meta.get_all_related_objects():
#             # Determine whether this related object is in another app.
#             # If it's in another app, the method names will have the app
#             # label prepended, and the add_BLAH() method will not be
#             # generated.
#             rel_mod = related.opts.get_model_module()
#             rel_obj_name = related.get_method_name_part()
#             if isinstance(related.field.rel, meta.OneToOne):
#                 # Add "get_thingie" methods for one-to-one related objects.
#                 # EXAMPLE: Place.get_restaurants_restaurant()
#                 func = curry(meta.method_get_related, 'get_object', rel_mod, related.field)
#                 func.__doc__ = "Returns the associated `%s.%s` object." % (related.opts.app_label, related.opts.module_name)
#                 setattr(klass, 'get_%s' % rel_obj_name, func)
#             elif isinstance(related.field.rel, meta.ManyToOne):
#                 # Add "get_thingie" methods for many-to-one related objects.
#                 # EXAMPLE: Poll.get_choice()
#                 func = curry(meta.method_get_related, 'get_object', rel_mod, related.field)
#                 func.__doc__ = "Returns the associated `%s.%s` object matching the given criteria." % \
#                     (related.opts.app_label, related.opts.module_name)
#                 setattr(klass, 'get_%s' % rel_obj_name, func)
#                 # Add "get_thingie_count" methods for many-to-one related objects.
#                 # EXAMPLE: Poll.get_choice_count()
#                 func = curry(meta.method_get_related, 'get_count', rel_mod, related.field)
#                 func.__doc__ = "Returns the number of associated `%s.%s` objects." % \
#                     (related.opts.app_label, related.opts.module_name)
#                 setattr(klass, 'get_%s_count' % rel_obj_name, func)
#                 # Add "get_thingie_list" methods for many-to-one related objects.
#                 # EXAMPLE: Poll.get_choice_list()
#                 func = curry(meta.method_get_related, 'get_list', rel_mod, related.field)
#                 func.__doc__ = "Returns a list of associated `%s.%s` objects." % \
#                      (related.opts.app_label, related.opts.module_name)
#                 setattr(klass, 'get_%s_list' % rel_obj_name, func)
#                 # Add "add_thingie" methods for many-to-one related objects,
#                 # but only for related objects that are in the same app.
#                 # EXAMPLE: Poll.add_choice()
#                 if related.opts.app_label == klass._meta.app_label:
#                     func = curry(meta.method_add_related, related.opts, rel_mod, related.field)
#                     func.alters_data = True
#                     setattr(klass, 'add_%s' % rel_obj_name, func)
#                 del func
#             del rel_obj_name, rel_mod, related # clean up
#
#         # Do the same for all related many-to-many objects.
#         for related in klass._meta.get_all_related_many_to_many_objects():
#             rel_mod = related.opts.get_model_module()
#             rel_obj_name = related.get_method_name_part()
#             setattr(klass, 'get_%s' % rel_obj_name, curry(meta.method_get_related_many_to_many, 'get_object', klass._meta, rel_mod, related.field))
#             setattr(klass, 'get_%s_count' % rel_obj_name, curry(meta.method_get_related_many_to_many, 'get_count', klass._meta, rel_mod, related.field))
#             setattr(klass, 'get_%s_list' % rel_obj_name, curry(meta.method_get_related_many_to_many, 'get_list', klass._meta, rel_mod, related.field))
#             if related.opts.app_label == klass._meta.app_label:
#                 func = curry(meta.method_set_related_many_to_many, related.opts, related.field)
#                 func.alters_data = True
#                 setattr(klass, 'set_%s' % related.opts.module_name, func)
#                 del func
#             del rel_obj_name, rel_mod, related # clean up
#
#         # Add "set_thingie_order" and "get_thingie_order" methods for objects
#         # that are ordered with respect to this.
#         for obj in klass._meta.get_ordered_objects():
#             func = curry(meta.method_set_order, obj)
#             func.__doc__ = "Sets the order of associated `%s.%s` objects to the given ID list." % (obj.app_label, obj.module_name)
#             func.alters_data = True
#             setattr(klass, 'set_%s_order' % obj.object_name.lower(), func)
#
#             func = curry(meta.method_get_order, obj)
#             func.__doc__ = "Returns the order of associated `%s.%s` objects as a list of IDs." % (obj.app_label, obj.module_name)
#             setattr(klass, 'get_%s_order' % obj.object_name.lower(), func)
#             del func, obj # clean up
#         del klass # clean up
#     del mod
# del modules
#
# # Expose get_app and get_module.
# from django.core.meta import get_app, get_module
