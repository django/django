from django import models
from django.core.xheaders import populate_xheaders
from django.core import template_loader, formfields
from django.views.auth.login import redirect_to_login
from django.core.extensions import DjangoContext as Context
from django.core.paginator import ObjectPaginator, InvalidPage
from django.utils.httpwrappers import HttpResponse, HttpResponseRedirect
from django.core.exceptions import Http404, ObjectDoesNotExist, ImproperlyConfigured

def create_object(request, app_label, module_name, template_name=None, 
                 template_loader=template_loader, extra_context={}, 
                 post_save_redirect=None, login_required=False, follow=None):
    """
    Generic object-creation function.
    
    Templates: ``<app_label>/<module_name>_form``
    Context:
        form
            the form wrapper for the object
    """
    if login_required and request.user.is_anonymous():
        return redirect_to_login(request.path)
        
    mod = models.get_module(app_label, module_name)
    manipulator = mod.AddManipulator(follow=follow)
    if request.POST:
        # If data was POSTed, we're trying to create a new object
        new_data = request.POST.copy()
        
        # Check for errors
        errors = manipulator.get_validation_errors(new_data)
        manipulator.do_html2python(new_data)
        
        if not errors:
            # No errors -- this means we can save the data!
            new_object = manipulator.save(new_data)
            
            if not request.user.is_anonymous():
                request.user.add_message("The %s was created sucessfully." % mod.Klass._meta.verbose_name)
            
            # Redirect to the new object: first by trying post_save_redirect,
            # then by obj.get_absolute_url; fail if neither works.
            if post_save_redirect:
                return HttpResponseRedirect(post_save_redirect % new_object.__dict__)
            elif hasattr(new_object, 'get_absolute_url'):
                return HttpResponseRedirect(new_object.get_absolute_url())
            else:
                raise ImproperlyConfigured("No URL to redirect to from generic create view.")
    else:
        # No POST, so we want a brand new form without any data or errors
        errors = {}
        new_data = manipulator.flatten_data()
    
    # Create the FormWrapper, template, context, response
    form = formfields.FormWrapper(manipulator, new_data, errors)
    if not template_name:
        template_name = "%s/%s_form" % (app_label, module_name)
    t = template_loader.get_template(template_name)
    c = Context(request, {
        'form' : form,
    })
    for key, value in extra_context.items():
        if callable(value):
            c[key] = value()
        else:   
            c[key] = value
    return HttpResponse(t.render(c))

def update_object(request, app_label, module_name, object_id=None, slug=None, 
                  slug_field=None, template_name=None, template_loader=template_loader,
                  extra_lookup_kwargs={}, extra_context={}, post_save_redirect=None, 
                  login_required=False, follow=None):
    """
    Generic object-update function.

    Templates: ``<app_label>/<module_name>_form``
    Context:
        form
            the form wrapper for the object
        object
            the original object being edited
    """
    if login_required and request.user.is_anonymous():
        return redirect_to_login(request.path)

    mod = models.get_module(app_label, module_name)
    
    # Look up the object to be edited
    lookup_kwargs = {}
    if object_id:
        lookup_kwargs['%s__exact' % mod.Klass._meta.pk.name] = object_id
    elif slug and slug_field:
        lookup_kwargs['%s__exact' % slug_field] = slug
    else:
        raise AttributeError("Generic edit view must be called with either an object_id or a slug/slug_field")
    lookup_kwargs.update(extra_lookup_kwargs)
    try:
        object = mod.get_object(**lookup_kwargs)
    except ObjectDoesNotExist:
        raise Http404("%s.%s does not exist for %s" % (app_label, module_name, lookup_kwargs))
    
    manipulator = mod.ChangeManipulator(object.id, follow=follow)
    
    if request.POST:
        new_data = request.POST.copy()
        errors = manipulator.get_validation_errors(new_data)
        manipulator.do_html2python(new_data)
        if not errors:
            manipulator.save(new_data)
            
            if not request.user.is_anonymous():
                request.user.add_message("The %s was updated sucessfully." % mod.Klass._meta.verbose_name)

            # Do a post-after-redirect so that reload works, etc.
            if post_save_redirect:
                return HttpResponseRedirect(post_save_redirect % object.__dict__)
            elif hasattr(object, 'get_absolute_url'):
                return HttpResponseRedirect(object.get_absolute_url())
            else:
                raise ImproperlyConfigured("No URL to redirect to from generic create view.")
    else:
        errors = {}
        # This makes sure the form acurate represents the fields of the place.
        new_data = manipulator.flatten_data()
    
    form = formfields.FormWrapper(manipulator, new_data, errors)
    if not template_name:
        template_name = "%s/%s_form" % (app_label, module_name)
    t = template_loader.get_template(template_name)
    c = Context(request, {
        'form' : form,
        'object' : object,
    })
    for key, value in extra_context.items():
        if callable(value):
            c[key] = value()
        else:   
            c[key] = value
    response = HttpResponse(t.render(c))
    populate_xheaders(request, response, app_label, module_name, getattr(object, object._meta.pk.name))
    return response

def delete_object(request, app_label, module_name, post_delete_redirect, 
                  object_id=None, slug=None, slug_field=None, template_name=None, 
                  template_loader=template_loader, extra_lookup_kwargs={}, 
                  extra_context={}, login_required=False):
    """
    Generic object-delete function.
    
    The given template will be used to confirm deletetion if this view is 
    fetched using GET; for safty, deletion will only be performed if this
    view is POSTed.

    Templates: ``<app_label>/<module_name>_confirm_delete``
    Context:
        object
            the original object being deleted
    """
    if login_required and request.user.is_anonymous():
        return redirect_to_login(request.path)

    mod = models.get_module(app_label, module_name)
    
    # Look up the object to be edited
    lookup_kwargs = {}
    if object_id:
        lookup_kwargs['%s__exact' % mod.Klass._meta.pk.name] = object_id
    elif slug and slug_field:
        lookup_kwargs['%s__exact' % slug_field] = slug
    else:
        raise AttributeError("Generic delete view must be called with either an object_id or a slug/slug_field")
    lookup_kwargs.update(extra_lookup_kwargs)
    try:
        object = mod.get_object(**lookup_kwargs)
    except ObjectDoesNotExist:
        raise Http404("%s.%s does not exist for %s" % (app_label, module_name, lookup_kwargs))
    
    if request.META['REQUEST_METHOD'] == 'POST':
        object.delete()
        if not request.user.is_anonymous():
            request.user.add_message("The %s was deleted." % mod.Klass._meta.verbose_name)
        return HttpResponseRedirect(post_delete_redirect)
    else:
        if not template_name:
            template_name = "%s/%s_confirm_delete" % (app_label, module_name)
        t = template_loader.get_template(template_name)
        c = Context(request, {
            'object' : object,
        })
        for key, value in extra_context.items():
            if callable(value):
                c[key] = value()
            else:   
                c[key] = value
        response = HttpResponse(t.render(c))
        populate_xheaders(request, response, app_label, module_name, getattr(object, object._meta.pk.name))
        return response

