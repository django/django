from django.contrib.admin import helpers
from django.core.urlresolvers import reverse
from django.db import models, transaction, router
from django.forms.formsets import all_valid
from django.http import Http404, HttpResponse, HttpResponseRedirect
from django.utils.decorators import method_decorator
from django.utils.encoding import force_text
from django.utils.html import escape, escapejs
from django.utils.translation import ugettext as _
from django.utils.translation import ugettext_lazy
from django.views.decorators.csrf import csrf_protect


csrf_protect_m = method_decorator(csrf_protect)


class AddItem(object):
    """
    The 'add' admin view for a model.
    """

    short_description = ugettext_lazy("Add %(verbose_name)s")
    css_class = "addlink"
    url = r'^add/$'
    name = 'add'

    def __call__(self, admin, request, *args, **kwargs):
        self.admin = admin
        return self.add_view(request, *args, **kwargs)

    def response_add(self, request, obj, post_url_continue='../%s/'):
        """
        Determines the HttpResponse for the add_view stage.
        """
        opts = obj._meta
        pk_value = obj._get_pk_val()

        msg = _('The %(name)s "%(obj)s" was added successfully.') % {'name': force_text(opts.verbose_name), 'obj': force_text(obj)}
        # Here, we distinguish between different save types by checking for
        # the presence of keys in request.POST.
        if "_continue" in request.POST:
            self.admin.message_user(request, msg + ' ' + _("You may edit it again below."))
            if "_popup" in request.POST:
                post_url_continue += "?_popup=1"
            return HttpResponseRedirect(post_url_continue % pk_value)

        if "_popup" in request.POST:
            return HttpResponse(
                '<!DOCTYPE html><html><head><title></title></head><body>'
                '<script type="text/javascript">opener.dismissAddAnotherPopup(window, "%s", "%s");</script></body></html>' % \
                # escape() calls force_text.
                (escape(pk_value), escapejs(obj)))
        elif "_addanother" in request.POST:
            self.admin.message_user(request, msg + ' ' + (_("You may add another %s below.") % force_text(opts.verbose_name)))
            return HttpResponseRedirect(request.path)
        else:
            self.admin.message_user(request, msg)

            # Figure out where to redirect. If the user has change permission,
            # redirect to the change-list page for this object. Otherwise,
            # redirect to the admin index.
            if self.admin.has_change_permission(request, None):
                post_url = reverse('admin:%s_%s_changelist' %
                                   (opts.app_label, opts.module_name),
                                   current_app=self.admin.admin_site.name)
            else:
                post_url = reverse('admin:index',
                                   current_app=self.admin.admin_site.name)
            return HttpResponseRedirect(post_url)

    @csrf_protect_m
    @transaction.commit_on_success
    def add_view(self, request, form_url='', extra_context=None):
        "The 'add' admin view for this model."
        model = self.admin.model
        opts = model._meta

        if not self.admin.has_add_permission(request):
            raise PermissionDenied

        ModelForm = self.admin.get_form(request)
        formsets = []
        inline_instances = self.admin.get_inline_instances(request)
        if request.method == 'POST':
            form = ModelForm(request.POST, request.FILES)
            if form.is_valid():
                new_object = self.admin.save_form(request, form, change=False)
                form_validated = True
            else:
                form_validated = False
                new_object = self.admin.model()
            prefixes = {}
            for FormSet, inline in zip(self.admin.get_formsets(request), inline_instances):
                prefix = FormSet.get_default_prefix()
                prefixes[prefix] = prefixes.get(prefix, 0) + 1
                if prefixes[prefix] != 1 or not prefix:
                    prefix = "%s-%s" % (prefix, prefixes[prefix])
                formset = FormSet(data=request.POST, files=request.FILES,
                                  instance=new_object,
                                  save_as_new="_saveasnew" in request.POST,
                                  prefix=prefix, queryset=inline.queryset(request))
                formsets.append(formset)
            if all_valid(formsets) and form_validated:
                self.admin.save_model(request, new_object, form, False)
                self.admin.save_related(request, form, formsets, False)
                self.admin.log_addition(request, new_object)
                return self.response_add(request, new_object)
        else:
            # Prepare the dict of initial data from the request.
            # We have to special-case M2Ms as a list of comma-separated PKs.
            initial = dict(request.GET.items())
            for k in initial:
                try:
                    f = opts.get_field(k)
                except models.FieldDoesNotExist:
                    continue
                if isinstance(f, models.ManyToManyField):
                    initial[k] = initial[k].split(",")
            form = ModelForm(initial=initial)
            prefixes = {}
            for FormSet, inline in zip(self.admin.get_formsets(request), inline_instances):
                prefix = FormSet.get_default_prefix()
                prefixes[prefix] = prefixes.get(prefix, 0) + 1
                if prefixes[prefix] != 1 or not prefix:
                    prefix = "%s-%s" % (prefix, prefixes[prefix])
                formset = FormSet(instance=self.admin.model(), prefix=prefix,
                                  queryset=inline.queryset(request))
                formsets.append(formset)

        adminForm = helpers.AdminForm(form, list(self.admin.get_fieldsets(request)),
            self.admin.get_prepopulated_fields(request),
            self.admin.get_readonly_fields(request),
            model_admin=self.admin)
        media = self.admin.media + adminForm.media

        inline_admin_formsets = []
        for inline, formset in zip(inline_instances, formsets):
            fieldsets = list(inline.get_fieldsets(request))
            readonly = list(inline.get_readonly_fields(request))
            prepopulated = dict(inline.get_prepopulated_fields(request))
            inline_admin_formset = helpers.InlineAdminFormSet(inline, formset,
                fieldsets, prepopulated, readonly, model_admin=self.admin)
            inline_admin_formsets.append(inline_admin_formset)
            media = media + inline_admin_formset.media

        context = {
            'title': _('Add %s') % force_text(opts.verbose_name),
            'adminform': adminForm,
            'is_popup': "_popup" in request.REQUEST,
            'media': media,
            'inline_admin_formsets': inline_admin_formsets,
            'errors': helpers.AdminErrorList(form, formsets),
            'app_label': opts.app_label,
        }
        context.update(extra_context or {})
        return self.admin.render_change_form(request, context, form_url=form_url, add=True)
