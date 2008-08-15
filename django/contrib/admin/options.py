from django import forms, template
from django.forms.formsets import all_valid
from django.forms.models import modelform_factory, inlineformset_factory
from django.forms.models import BaseInlineFormSet
from django.contrib.contenttypes.models import ContentType
from django.contrib.admin import widgets
from django.contrib.admin.util import quote, unquote, get_deleted_objects
from django.core.exceptions import PermissionDenied
from django.db import models, transaction
from django.http import Http404, HttpResponse, HttpResponseRedirect
from django.shortcuts import get_object_or_404, render_to_response
from django.utils.html import escape
from django.utils.safestring import mark_safe
from django.utils.text import capfirst, get_text_list
from django.utils.translation import ugettext as _
from django.utils.encoding import force_unicode
try:
    set
except NameError:
    from sets import Set as set     # Python 2.3 fallback

HORIZONTAL, VERTICAL = 1, 2
# returns the <ul> class for a given radio_admin field
get_ul_class = lambda x: 'radiolist%s' % ((x == HORIZONTAL) and ' inline' or '')

class IncorrectLookupParameters(Exception):
    pass

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

class AdminForm(object):
    def __init__(self, form, fieldsets, prepopulated_fields):
        self.form, self.fieldsets = form, fieldsets
        self.prepopulated_fields = [{
            'field': form[field_name],
            'dependencies': [form[f] for f in dependencies]
        } for field_name, dependencies in prepopulated_fields.items()]

    def __iter__(self):
        for name, options in self.fieldsets:
            yield Fieldset(self.form, name, **options)

    def first_field(self):
        for bf in self.form:
            return bf

    def _media(self):
        media = self.form.media
        for fs in self:
            media = media + fs.media
        return media
    media = property(_media)

class Fieldset(object):
    def __init__(self, form, name=None, fields=(), classes=(), description=None):
        self.form = form
        self.name, self.fields = name, fields
        self.classes = u' '.join(classes)
        self.description = description

    def _media(self):
        from django.conf import settings
        if 'collapse' in self.classes:
            return forms.Media(js=['%sjs/admin/CollapsedFieldsets.js' % settings.ADMIN_MEDIA_PREFIX])
        return forms.Media()
    media = property(_media)

    def __iter__(self):
        for field in self.fields:
            yield Fieldline(self.form, field)

class Fieldline(object):
    def __init__(self, form, field):
        self.form = form # A django.forms.Form instance
        if isinstance(field, basestring):
            self.fields = [field]
        else:
            self.fields = field

    def __iter__(self):
        for i, field in enumerate(self.fields):
            yield AdminField(self.form, field, is_first=(i == 0))

    def errors(self):
        return mark_safe(u'\n'.join([self.form[f].errors.as_ul() for f in self.fields]).strip('\n'))

class AdminField(object):
    def __init__(self, form, field, is_first):
        self.field = form[field] # A django.forms.BoundField instance
        self.is_first = is_first # Whether this field is first on the line
        self.is_checkbox = isinstance(self.field.field.widget, forms.CheckboxInput)

    def label_tag(self):
        classes = []
        if self.is_checkbox:
            classes.append(u'vCheckboxLabel')
            contents = force_unicode(escape(self.field.label))
        else:
            contents = force_unicode(escape(self.field.label)) + u':'
        if self.field.field.required:
            classes.append(u'required')
        if not self.is_first:
            classes.append(u'inline')
        attrs = classes and {'class': u' '.join(classes)} or {}
        return self.field.label_tag(contents=contents, attrs=attrs)

class BaseModelAdmin(object):
    """Functionality common to both ModelAdmin and InlineAdmin."""
    raw_id_fields = ()
    fields = None
    fieldsets = None
    form = forms.ModelForm
    filter_vertical = ()
    filter_horizontal = ()
    radio_fields = {}
    prepopulated_fields = {}

    def formfield_for_dbfield(self, db_field, **kwargs):
        """
        Hook for specifying the form Field instance for a given database Field
        instance.

        If kwargs are given, they're passed to the form Field's constructor.
        """
        
        # If the field specifies choices, we don't need to look for special
        # admin widgets - we just need to use a select widget of some kind.
        if db_field.choices:
            if db_field.name in self.radio_fields:
                # If the field is named as a radio_field, use a RadioSelect
                kwargs['widget'] = widgets.AdminRadioSelect(
                    choices=db_field.get_choices(include_blank=db_field.blank,
                        blank_choice=[('', _('None'))]),
                    attrs={
                        'class': get_ul_class(self.radio_fields[db_field.name]),
                    }
                )
                return db_field.formfield(**kwargs)
            else:
                # Otherwise, use the default select widget.
                return db_field.formfield(**kwargs)

        # For DateTimeFields, use a special field and widget.
        if isinstance(db_field, models.DateTimeField):
            kwargs['form_class'] = forms.SplitDateTimeField
            kwargs['widget'] = widgets.AdminSplitDateTime()
            return db_field.formfield(**kwargs)

        # For DateFields, add a custom CSS class.
        if isinstance(db_field, models.DateField):
            kwargs['widget'] = widgets.AdminDateWidget
            return db_field.formfield(**kwargs)

        # For TimeFields, add a custom CSS class.
        if isinstance(db_field, models.TimeField):
            kwargs['widget'] = widgets.AdminTimeWidget
            return db_field.formfield(**kwargs)
        
        # For TextFields, add a custom CSS class.
        if isinstance(db_field, models.TextField):
            kwargs['widget'] = widgets.AdminTextareaWidget
            return db_field.formfield(**kwargs)
        
        # For URLFields, add a custom CSS class.
        if isinstance(db_field, models.URLField):
            kwargs['widget'] = widgets.AdminURLFieldWidget
            return db_field.formfield(**kwargs)
        
        # For IntegerFields, add a custom CSS class.
        if isinstance(db_field, models.IntegerField):
            kwargs['widget'] = widgets.AdminIntegerFieldWidget
            return db_field.formfield(**kwargs)

        # For TextInputs, add a custom CSS class.
        if isinstance(db_field, models.CharField):
            kwargs['widget'] = widgets.AdminTextInputWidget
            return db_field.formfield(**kwargs)
    
        # For FileFields and ImageFields add a link to the current file.
        if isinstance(db_field, models.ImageField) or isinstance(db_field, models.FileField):
            kwargs['widget'] = widgets.AdminFileWidget
            return db_field.formfield(**kwargs)

        # For ForeignKey or ManyToManyFields, use a special widget.
        if isinstance(db_field, (models.ForeignKey, models.ManyToManyField)):
            if isinstance(db_field, models.ForeignKey) and db_field.name in self.raw_id_fields:
                kwargs['widget'] = widgets.ForeignKeyRawIdWidget(db_field.rel)
            elif isinstance(db_field, models.ForeignKey) and db_field.name in self.radio_fields:
                kwargs['widget'] = widgets.AdminRadioSelect(attrs={
                    'class': get_ul_class(self.radio_fields[db_field.name]),
                })
                kwargs['empty_label'] = db_field.blank and _('None') or None
            else:
                if isinstance(db_field, models.ManyToManyField):
                    # If it uses an intermediary model, don't show field in admin.
                    if db_field.rel.through is not None:
                        return None
                    elif db_field.name in self.raw_id_fields:
                        kwargs['widget'] = widgets.ManyToManyRawIdWidget(db_field.rel)
                        kwargs['help_text'] = ''
                    elif db_field.name in (list(self.filter_vertical) + list(self.filter_horizontal)):
                        kwargs['widget'] = widgets.FilteredSelectMultiple(db_field.verbose_name, (db_field.name in self.filter_vertical))
            # Wrap the widget's render() method with a method that adds
            # extra HTML to the end of the rendered output.
            formfield = db_field.formfield(**kwargs)
            # Don't wrap raw_id fields. Their add function is in the popup window.
            if not db_field.name in self.raw_id_fields:
                formfield.widget = widgets.RelatedFieldWidgetWrapper(formfield.widget, db_field.rel, self.admin_site)
            return formfield

        # For any other type of field, just call its formfield() method.
        return db_field.formfield(**kwargs)

    def _declared_fieldsets(self):
        if self.fieldsets:
            return self.fieldsets
        elif self.fields:
            return [(None, {'fields': self.fields})]
        return None
    declared_fieldsets = property(_declared_fieldsets)

class ModelAdmin(BaseModelAdmin):
    "Encapsulates all admin options and functionality for a given model."
    __metaclass__ = forms.MediaDefiningClass

    list_display = ('__str__',)
    list_display_links = ()
    list_filter = ()
    list_select_related = False
    list_per_page = 100
    search_fields = ()
    date_hierarchy = None
    save_as = False
    save_on_top = False
    ordering = None
    inlines = []

    # Custom templates (designed to be over-ridden in subclasses)
    change_form_template = None
    change_list_template = None
    delete_confirmation_template = None
    object_history_template = None

    def __init__(self, model, admin_site):
        self.model = model
        self.opts = model._meta
        self.admin_site = admin_site
        self.inline_instances = []
        for inline_class in self.inlines:
            inline_instance = inline_class(self.model, self.admin_site)
            self.inline_instances.append(inline_instance)
        super(ModelAdmin, self).__init__()

    def __call__(self, request, url):
        # Delegate to the appropriate method, based on the URL.
        if url is None:
            return self.changelist_view(request)
        elif url.endswith('add'):
            return self.add_view(request)
        elif url.endswith('history'):
            return self.history_view(request, unquote(url[:-8]))
        elif url.endswith('delete'):
            return self.delete_view(request, unquote(url[:-7]))
        else:
            return self.change_view(request, unquote(url))

    def _media(self):
        from django.conf import settings

        js = ['js/core.js', 'js/admin/RelatedObjectLookups.js']
        if self.prepopulated_fields:
            js.append('js/urlify.js')
        if self.opts.get_ordered_objects():
            js.extend(['js/getElementsBySelector.js', 'js/dom-drag.js' , 'js/admin/ordering.js'])
        if self.filter_vertical or self.filter_horizontal:
            js.extend(['js/SelectBox.js' , 'js/SelectFilter2.js'])

        return forms.Media(js=['%s%s' % (settings.ADMIN_MEDIA_PREFIX, url) for url in js])
    media = property(_media)

    def has_add_permission(self, request):
        "Returns True if the given request has permission to add an object."
        opts = self.opts
        return request.user.has_perm(opts.app_label + '.' + opts.get_add_permission())

    def has_change_permission(self, request, obj=None):
        """
        Returns True if the given request has permission to change the given
        Django model instance.

        If `obj` is None, this should return True if the given request has
        permission to change *any* object of the given type.
        """
        opts = self.opts
        return request.user.has_perm(opts.app_label + '.' + opts.get_change_permission())

    def has_delete_permission(self, request, obj=None):
        """
        Returns True if the given request has permission to change the given
        Django model instance.

        If `obj` is None, this should return True if the given request has
        permission to delete *any* object of the given type.
        """
        opts = self.opts
        return request.user.has_perm(opts.app_label + '.' + opts.get_delete_permission())

    def queryset(self, request):
        """
        Returns a QuerySet of all model instances that can be edited by the
        admin site. This is used by changelist_view.
        """
        qs = self.model._default_manager.get_query_set()
        # TODO: this should be handled by some parameter to the ChangeList.
        ordering = self.ordering or () # otherwise we might try to *None, which is bad ;)
        if ordering:
            qs = qs.order_by(*ordering)
        return qs

    def get_fieldsets(self, request, obj=None):
        "Hook for specifying fieldsets for the add form."
        if self.declared_fieldsets:
            return self.declared_fieldsets
        form = self.get_form(request)
        return [(None, {'fields': form.base_fields.keys()})]

    def get_form(self, request, obj=None):
        """
        Returns a Form class for use in the admin add view. This is used by
        add_view and change_view.
        """
        if self.declared_fieldsets:
            fields = flatten_fieldsets(self.declared_fieldsets)
        else:
            fields = None
        return modelform_factory(self.model, form=self.form, fields=fields, formfield_callback=self.formfield_for_dbfield)

    def get_formsets(self, request, obj=None):
        for inline in self.inline_instances:
            yield inline.get_formset(request, obj)
            
    def log_addition(self, request, object):
        """
        Log that an object has been successfully added. 
        
        The default implementation creates an admin LogEntry object.
        """
        from django.contrib.admin.models import LogEntry, ADDITION
        LogEntry.objects.log_action(
            user_id         = request.user.pk, 
            content_type_id = ContentType.objects.get_for_model(object).pk,
            object_id       = object.pk,
            object_repr     = force_unicode(object), 
            action_flag     = ADDITION
        )
        
    def log_change(self, request, object, message):
        """
        Log that an object has been successfully changed. 
        
        The default implementation creates an admin LogEntry object.
        """
        from django.contrib.admin.models import LogEntry, CHANGE
        LogEntry.objects.log_action(
            user_id         = request.user.pk, 
            content_type_id = ContentType.objects.get_for_model(object).pk, 
            object_id       = object.pk, 
            object_repr     = force_unicode(object), 
            action_flag     = CHANGE, 
            change_message  = message
        )
        
    def log_deletion(self, request, object, object_repr):
        """
        Log that an object has been successfully deleted. Note that since the
        object is deleted, it might no longer be safe to call *any* methods
        on the object, hence this method getting object_repr.
        
        The default implementation creates an admin LogEntry object.
        """
        from django.contrib.admin.models import LogEntry, DELETION
        LogEntry.objects.log_action(
            user_id         = request.user.id, 
            content_type_id = ContentType.objects.get_for_model(self.model).pk, 
            object_id       = object.pk, 
            object_repr     = object_repr,
            action_flag     = DELETION
        )
        
    
    def construct_change_message(self, request, form, formsets):
        """
        Construct a change message from a changed object.
        """
        change_message = []
        if form.changed_data:
            change_message.append(_('Changed %s.') % get_text_list(form.changed_data, _('and')))

        if formsets:
            for formset in formsets:
                for added_object in formset.new_objects:
                    change_message.append(_('Added %(name)s "%(object)s".')
                                          % {'name': added_object._meta.verbose_name,
                                             'object': added_object})
                for changed_object, changed_fields in formset.changed_objects:
                    change_message.append(_('Changed %(list)s for %(name)s "%(object)s".')
                                          % {'list': get_text_list(changed_fields, _('and')),
                                             'name': changed_object._meta.verbose_name,
                                             'object': changed_object})
                for deleted_object in formset.deleted_objects:
                    change_message.append(_('Deleted %(name)s "%(object)s".')
                                          % {'name': deleted_object._meta.verbose_name,
                                             'object': deleted_object})
        change_message = ' '.join(change_message)
        return change_message or _('No fields changed.')
    
    def message_user(self, request, message):
        """
        Send a message to the user. The default implementation 
        posts a message using the auth Message object.
        """
        request.user.message_set.create(message=message)

    def save_form(self, request, form, change):
        """
        Given a ModelForm return an unsaved instance. ``change`` is True if
        the object is being changed, and False if it's being added.
        """
        return form.save(commit=False)
    
    def save_model(self, request, obj, form, change):
        """
        Given a model instance save it to the database.
        """
        obj.save()

    def save_formset(self, request, form, formset, change):
        """
        Given an inline formset save it to the database.
        """
        formset.save()

    def render_change_form(self, request, context, add=False, change=False, form_url='', obj=None):
        opts = self.model._meta
        app_label = opts.app_label
        ordered_objects = opts.get_ordered_objects()
        context.update({
            'add': add,
            'change': change,
            'has_add_permission': self.has_add_permission(request),
            'has_change_permission': self.has_change_permission(request, obj),
            'has_delete_permission': self.has_delete_permission(request, obj),
            'has_file_field': True, # FIXME - this should check if form or formsets have a FileField,
            'has_absolute_url': hasattr(self.model, 'get_absolute_url'),
            'ordered_objects': ordered_objects,
            'form_url': mark_safe(form_url),
            'opts': opts,
            'content_type_id': ContentType.objects.get_for_model(self.model).id,
            'save_as': self.save_as,
            'save_on_top': self.save_on_top,
            'root_path': self.admin_site.root_path,
        })
        return render_to_response(self.change_form_template or [
            "admin/%s/%s/change_form.html" % (app_label, opts.object_name.lower()),
            "admin/%s/change_form.html" % app_label,
            "admin/change_form.html"
        ], context, context_instance=template.RequestContext(request))
    
    def response_add(self, request, obj, post_url_continue='../%s/'):
        """
        Determines the HttpResponse for the add_view stage.
        """
        opts = obj._meta
        pk_value = obj._get_pk_val()
        
        msg = _('The %(name)s "%(obj)s" was added successfully.') % {'name': force_unicode(opts.verbose_name), 'obj': force_unicode(obj)}
        # Here, we distinguish between different save types by checking for
        # the presence of keys in request.POST.
        if request.POST.has_key("_continue"):
            self.message_user(request, msg + ' ' + _("You may edit it again below."))
            if request.POST.has_key("_popup"):
                post_url_continue += "?_popup=1"
            return HttpResponseRedirect(post_url_continue % pk_value)
        
        if request.POST.has_key("_popup"):
            return HttpResponse('<script type="text/javascript">opener.dismissAddAnotherPopup(window, "%s", "%s");</script>' % \
                # escape() calls force_unicode.
                (escape(pk_value), escape(obj)))
        elif request.POST.has_key("_addanother"):
            self.message_user(request, msg + ' ' + (_("You may add another %s below.") % force_unicode(opts.verbose_name)))
            return HttpResponseRedirect(request.path)
        else:
            self.message_user(request, msg)

            # Figure out where to redirect. If the user has change permission,
            # redirect to the change-list page for this object. Otherwise,
            # redirect to the admin index.
            if self.has_change_permission(request, None):
                post_url = '../'
            else:
                post_url = '../../../'
            return HttpResponseRedirect(post_url)
    
    def response_change(self, request, obj):
        """
        Determines the HttpResponse for the change_view stage.
        """
        opts = obj._meta
        pk_value = obj._get_pk_val()
        
        msg = _('The %(name)s "%(obj)s" was changed successfully.') % {'name': force_unicode(opts.verbose_name), 'obj': force_unicode(obj)}
        if request.POST.has_key("_continue"):
            self.message_user(request, msg + ' ' + _("You may edit it again below."))
            if request.REQUEST.has_key('_popup'):
                return HttpResponseRedirect(request.path + "?_popup=1")
            else:
                return HttpResponseRedirect(request.path)
        elif request.POST.has_key("_saveasnew"):
            msg = _('The %(name)s "%(obj)s" was added successfully. You may edit it again below.') % {'name': force_unicode(opts.verbose_name), 'obj': obj}
            self.message_user(request, msg)
            return HttpResponseRedirect("../%s/" % pk_value)
        elif request.POST.has_key("_addanother"):
            self.message_user(request, msg + ' ' + (_("You may add another %s below.") % force_unicode(opts.verbose_name)))
            return HttpResponseRedirect("../add/")
        else:
            self.message_user(request, msg)
            return HttpResponseRedirect("../")

    def add_view(self, request, form_url='', extra_context=None):
        "The 'add' admin view for this model."
        model = self.model
        opts = model._meta
        app_label = opts.app_label

        if not self.has_add_permission(request):
            raise PermissionDenied

        if self.has_change_permission(request, None):
            # redirect to list view
            post_url = '../'
        else:
            # Object list will give 'Permission Denied', so go back to admin home
            post_url = '../../../'

        ModelForm = self.get_form(request)
        formsets = []
        if request.method == 'POST':
            form = ModelForm(request.POST, request.FILES)
            if form.is_valid():
                form_validated = True
                new_object = self.save_form(request, form, change=False)
            else:
                form_validated = False
                new_object = self.model()
            for FormSet in self.get_formsets(request):
                formset = FormSet(data=request.POST, files=request.FILES,
                                  instance=new_object,
                                  save_as_new=request.POST.has_key("_saveasnew"))
                formsets.append(formset)
            if all_valid(formsets) and form_validated:
                self.save_model(request, new_object, form, change=False)
                form.save_m2m()
                for formset in formsets:
                    self.save_formset(request, form, formset, change=False)
                
                self.log_addition(request, new_object)
                return self.response_add(request, new_object)
        else:
            form = ModelForm(initial=dict(request.GET.items()))
            for FormSet in self.get_formsets(request):
                formset = FormSet(instance=self.model())
                formsets.append(formset)

        adminForm = AdminForm(form, list(self.get_fieldsets(request)), self.prepopulated_fields)
        media = self.media + adminForm.media

        inline_admin_formsets = []
        for inline, formset in zip(self.inline_instances, formsets):
            fieldsets = list(inline.get_fieldsets(request))
            inline_admin_formset = InlineAdminFormSet(inline, formset, fieldsets)
            inline_admin_formsets.append(inline_admin_formset)
            media = media + inline_admin_formset.media

        context = {
            'title': _('Add %s') % force_unicode(opts.verbose_name),
            'adminform': adminForm,
            'is_popup': request.REQUEST.has_key('_popup'),
            'show_delete': False,
            'media': mark_safe(media),
            'inline_admin_formsets': inline_admin_formsets,
            'errors': AdminErrorList(form, formsets),
            'root_path': self.admin_site.root_path,
        }
        context.update(extra_context or {})
        return self.render_change_form(request, context, add=True)
    add_view = transaction.commit_on_success(add_view)

    def change_view(self, request, object_id, extra_context=None):
        "The 'change' admin view for this model."
        model = self.model
        opts = model._meta
        app_label = opts.app_label

        try:
            obj = model._default_manager.get(pk=object_id)
        except model.DoesNotExist:
            # Don't raise Http404 just yet, because we haven't checked
            # permissions yet. We don't want an unauthenticated user to be able
            # to determine whether a given object exists.
            obj = None

        if not self.has_change_permission(request, obj):
            raise PermissionDenied

        if obj is None:
            raise Http404('%s object with primary key %r does not exist.' % (force_unicode(opts.verbose_name), escape(object_id)))

        if request.POST and request.POST.has_key("_saveasnew"):
            return self.add_view(request, form_url='../../add/')

        ModelForm = self.get_form(request, obj)
        formsets = []
        if request.method == 'POST':
            form = ModelForm(request.POST, request.FILES, instance=obj)
            if form.is_valid():
                form_validated = True
                new_object = self.save_form(request, form, change=True)
            else:
                form_validated = False
                new_object = obj
            for FormSet in self.get_formsets(request, new_object):
                formset = FormSet(request.POST, request.FILES,
                                  instance=new_object)
                formsets.append(formset)

            if all_valid(formsets) and form_validated:
                self.save_model(request, new_object, form, change=True)
                form.save_m2m()
                for formset in formsets:
                    self.save_formset(request, form, formset, change=True)
                
                change_message = self.construct_change_message(request, form, formsets)
                self.log_change(request, new_object, change_message)
                return self.response_change(request, new_object)
        else:
            form = ModelForm(instance=obj)
            for FormSet in self.get_formsets(request, obj):
                formset = FormSet(instance=obj)
                formsets.append(formset)

        adminForm = AdminForm(form, self.get_fieldsets(request, obj), self.prepopulated_fields)
        media = self.media + adminForm.media

        inline_admin_formsets = []
        for inline, formset in zip(self.inline_instances, formsets):
            fieldsets = list(inline.get_fieldsets(request, obj))
            inline_admin_formset = InlineAdminFormSet(inline, formset, fieldsets)
            inline_admin_formsets.append(inline_admin_formset)
            media = media + inline_admin_formset.media

        context = {
            'title': _('Change %s') % force_unicode(opts.verbose_name),
            'adminform': adminForm,
            'object_id': object_id,
            'original': obj,
            'is_popup': request.REQUEST.has_key('_popup'),
            'media': mark_safe(media),
            'inline_admin_formsets': inline_admin_formsets,
            'errors': AdminErrorList(form, formsets),
            'root_path': self.admin_site.root_path,
        }
        context.update(extra_context or {})
        return self.render_change_form(request, context, change=True, obj=obj)
    change_view = transaction.commit_on_success(change_view)

    def changelist_view(self, request, extra_context=None):
        "The 'change list' admin view for this model."
        from django.contrib.admin.views.main import ChangeList, ERROR_FLAG
        opts = self.model._meta
        app_label = opts.app_label
        if not self.has_change_permission(request, None):
            raise PermissionDenied
        try:
            cl = ChangeList(request, self.model, self.list_display, self.list_display_links, self.list_filter,
                self.date_hierarchy, self.search_fields, self.list_select_related, self.list_per_page, self)
        except IncorrectLookupParameters:
            # Wacky lookup parameters were given, so redirect to the main
            # changelist page, without parameters, and pass an 'invalid=1'
            # parameter via the query string. If wacky parameters were given and
            # the 'invalid=1' parameter was already in the query string, something
            # is screwed up with the database, so display an error page.
            if ERROR_FLAG in request.GET.keys():
                return render_to_response('admin/invalid_setup.html', {'title': _('Database error')})
            return HttpResponseRedirect(request.path + '?' + ERROR_FLAG + '=1')

        context = {
            'title': cl.title,
            'is_popup': cl.is_popup,
            'cl': cl,
            'has_add_permission': self.has_add_permission(request),
            'root_path': self.admin_site.root_path,
        }
        context.update(extra_context or {})
        return render_to_response(self.change_list_template or [
            'admin/%s/%s/change_list.html' % (app_label, opts.object_name.lower()),
            'admin/%s/change_list.html' % app_label,
            'admin/change_list.html'
        ], context, context_instance=template.RequestContext(request))

    def delete_view(self, request, object_id, extra_context=None):
        "The 'delete' admin view for this model."
        opts = self.model._meta
        app_label = opts.app_label

        try:
            obj = self.model._default_manager.get(pk=object_id)
        except self.model.DoesNotExist:
            # Don't raise Http404 just yet, because we haven't checked
            # permissions yet. We don't want an unauthenticated user to be able
            # to determine whether a given object exists.
            obj = None

        if not self.has_delete_permission(request, obj):
            raise PermissionDenied

        if obj is None:
            raise Http404('%s object with primary key %r does not exist.' % (force_unicode(opts.verbose_name), escape(object_id)))

        # Populate deleted_objects, a data structure of all related objects that
        # will also be deleted.
        deleted_objects = [mark_safe(u'%s: <a href="../../%s/">%s</a>' % (escape(force_unicode(capfirst(opts.verbose_name))), quote(object_id), escape(obj))), []]
        perms_needed = set()
        get_deleted_objects(deleted_objects, perms_needed, request.user, obj, opts, 1, self.admin_site)

        if request.POST: # The user has already confirmed the deletion.
            if perms_needed:
                raise PermissionDenied
            obj_display = str(obj)
            obj.delete()
            
            self.log_deletion(request, obj, obj_display)
            self.message_user(request, _('The %(name)s "%(obj)s" was deleted successfully.') % {'name': force_unicode(opts.verbose_name), 'obj': force_unicode(obj_display)})
            
            if not self.has_change_permission(request, None):
                return HttpResponseRedirect("../../../../")
            return HttpResponseRedirect("../../")

        context = {
            "title": _("Are you sure?"),
            "object_name": force_unicode(opts.verbose_name),
            "object": obj,
            "deleted_objects": deleted_objects,
            "perms_lacking": perms_needed,
            "opts": opts,
            "root_path": self.admin_site.root_path,
        }
        context.update(extra_context or {})
        return render_to_response(self.delete_confirmation_template or [
            "admin/%s/%s/delete_confirmation.html" % (app_label, opts.object_name.lower()),
            "admin/%s/delete_confirmation.html" % app_label,
            "admin/delete_confirmation.html"
        ], context, context_instance=template.RequestContext(request))

    def history_view(self, request, object_id, extra_context=None):
        "The 'history' admin view for this model."
        from django.contrib.admin.models import LogEntry
        model = self.model
        opts = model._meta
        action_list = LogEntry.objects.filter(
            object_id = object_id,
            content_type__id__exact = ContentType.objects.get_for_model(model).id
        ).select_related().order_by('action_time')
        # If no history was found, see whether this object even exists.
        obj = get_object_or_404(model, pk=object_id)
        context = {
            'title': _('Change history: %s') % force_unicode(obj),
            'action_list': action_list,
            'module_name': capfirst(force_unicode(opts.verbose_name_plural)),
            'object': obj,
            'root_path': self.admin_site.root_path,
        }
        context.update(extra_context or {})
        return render_to_response(self.object_history_template or [
            "admin/%s/%s/object_history.html" % (opts.app_label, opts.object_name.lower()),
            "admin/%s/object_history.html" % opts.app_label,
            "admin/object_history.html"
        ], context, context_instance=template.RequestContext(request))

class InlineModelAdmin(BaseModelAdmin):
    """
    Options for inline editing of ``model`` instances.

    Provide ``name`` to specify the attribute name of the ``ForeignKey`` from
    ``model`` to its parent. This is required if ``model`` has more than one
    ``ForeignKey`` to its parent.
    """
    model = None
    fk_name = None
    formset = BaseInlineFormSet
    extra = 3
    max_num = 0
    template = None
    verbose_name = None
    verbose_name_plural = None

    def __init__(self, parent_model, admin_site):
        self.admin_site = admin_site
        self.parent_model = parent_model
        self.opts = self.model._meta
        super(InlineModelAdmin, self).__init__()
        if self.verbose_name is None:
            self.verbose_name = self.model._meta.verbose_name
        if self.verbose_name_plural is None:
            self.verbose_name_plural = self.model._meta.verbose_name_plural

    def get_formset(self, request, obj=None):
        """Returns a BaseInlineFormSet class for use in admin add/change views."""
        if self.declared_fieldsets:
            fields = flatten_fieldsets(self.declared_fieldsets)
        else:
            fields = None
        return inlineformset_factory(self.parent_model, self.model,
            form=self.form, formset=self.formset, fk_name=self.fk_name,
            fields=fields, formfield_callback=self.formfield_for_dbfield,
            extra=self.extra, max_num=self.max_num)

    def get_fieldsets(self, request, obj=None):
        if self.declared_fieldsets:
            return self.declared_fieldsets
        form = self.get_formset(request).form
        return [(None, {'fields': form.base_fields.keys()})]

class StackedInline(InlineModelAdmin):
    template = 'admin/edit_inline/stacked.html'

class TabularInline(InlineModelAdmin):
    template = 'admin/edit_inline/tabular.html'

class InlineAdminFormSet(object):
    """
    A wrapper around an inline formset for use in the admin system.
    """
    def __init__(self, inline, formset, fieldsets):
        self.opts = inline
        self.formset = formset
        self.fieldsets = fieldsets

    def __iter__(self):
        for form, original in zip(self.formset.initial_forms, self.formset.get_queryset()):
            yield InlineAdminForm(self.formset, form, self.fieldsets, self.opts.prepopulated_fields, original)
        for form in self.formset.extra_forms:
            yield InlineAdminForm(self.formset, form, self.fieldsets, self.opts.prepopulated_fields, None)

    def fields(self):
        for field_name in flatten_fieldsets(self.fieldsets):
            yield self.formset.form.base_fields[field_name]

    def _media(self):
        media = self.formset.media
        for fs in self:
            media = media + fs.media
        return media
    media = property(_media)

class InlineAdminForm(AdminForm):
    """
    A wrapper around an inline form for use in the admin system.
    """
    def __init__(self, formset, form, fieldsets, prepopulated_fields, original):
        self.formset = formset
        self.original = original
        self.show_url = original and hasattr(original, 'get_absolute_url')
        super(InlineAdminForm, self).__init__(form, fieldsets, prepopulated_fields)

    def pk_field(self):
        return AdminField(self.form, self.formset._pk_field_name, False)

    def deletion_field(self):
        from django.forms.formsets import DELETION_FIELD_NAME
        return AdminField(self.form, DELETION_FIELD_NAME, False)

    def ordering_field(self):
        from django.forms.formsets import ORDERING_FIELD_NAME
        return AdminField(self.form, ORDERING_FIELD_NAME, False)

class AdminErrorList(forms.util.ErrorList):
    """
    Stores all errors for the form/formsets in an add/change stage view.
    """
    def __init__(self, form, inline_formsets):
        if form.is_bound:
            self.extend(form.errors.values())
            for inline_formset in inline_formsets:
                self.extend(inline_formset.non_form_errors())
                for errors_in_inline_form in inline_formset.errors:
                    self.extend(errors_in_inline_form.values())
