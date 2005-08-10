from django.core import meta, validators

class Site(meta.Model):
    db_table = 'sites'
    fields = (
        meta.CharField('domain', 'domain name', maxlength=100),
        meta.CharField('name', 'display name', maxlength=50),
    )
    ordering = ('domain',)

    def __repr__(self):
        return self.domain

    def _module_get_current():
        "Returns the current site, according to the SITE_ID constant."
        from django.conf.settings import SITE_ID
        return get_object(pk=SITE_ID)

class Package(meta.Model):
    db_table = 'packages'
    fields = (
        meta.CharField('label', maxlength=20, primary_key=True),
        meta.CharField('name', maxlength=30, unique=True),
    )
    ordering = ('name',)

    def __repr__(self):
        return self.name

class ContentType(meta.Model):
    db_table = 'content_types'
    fields = (
        meta.CharField('name', maxlength=100),
        meta.ForeignKey(Package, name='package'),
        meta.CharField('python_module_name', maxlength=50),
    )
    ordering = ('package', 'name')
    unique_together = (('package', 'python_module_name'),)

    def __repr__(self):
        return "%s | %s" % (self.package, self.name)

    def get_model_module(self):
        "Returns the Python model module for accessing this type of content."
        return __import__('django.models.%s.%s' % (self.package, self.python_module_name), '', '', [''])

    def get_object_for_this_type(self, **kwargs):
        """
        Returns an object of this type for the keyword arguments given.
        Basically, this is a proxy around this object_type's get_object() model
        method. The ObjectNotExist exception, if thrown, will not be caught,
        so code that calls this method should catch it.
        """
        return self.get_model_module().get_object(**kwargs)

class Redirect(meta.Model):
    db_table = 'redirects'
    fields = (
        meta.ForeignKey(Site, radio_admin=meta.VERTICAL),
        meta.CharField('old_path', 'redirect from', maxlength=200, db_index=True,
            help_text="This should be an absolute path, excluding the domain name. Example: '/events/search/'."),
        meta.CharField('new_path', 'redirect to', maxlength=200, blank=True,
            help_text="This can be either an absolute path (as above) or a full URL starting with 'http://'."),
    )
    unique_together=(('site_id', 'old_path'),)
    ordering = ('old_path',)
    admin = meta.Admin(
        list_display = ('__repr__',),
        list_filter = ('site_id',),
        search_fields = ('old_path', 'new_path'),
    )

    def __repr__(self):
        return "%s ---> %s" % (self.old_path, self.new_path)

class FlatFile(meta.Model):
    db_table = 'flatfiles'
    verbose_name = 'flat page'
    fields = (
        meta.CharField('url', 'URL', maxlength=100, validator_list=[validators.isAlphaNumericURL],
            help_text="Example: '/about/contact/'. Make sure to have leading and trailing slashes."),
        meta.CharField('title', maxlength=200),
        meta.TextField('content', help_text="Full HTML is allowed."),
        meta.BooleanField('enable_comments'),
        meta.CharField('template_name', maxlength=70, blank=True,
            help_text="Example: 'flatfiles/contact_page'. If this isn't provided, the system will use 'flatfiles/default'."),
        meta.BooleanField('registration_required',
            help_text="If this is checked, only logged-in users will be able to view the page."),
        meta.ManyToManyField(Site),
    )
    ordering = ('url',)
    admin = meta.Admin(
        fields = (
            (None, {'fields': ('url', 'title', 'content', 'sites')}),
            ('Advanced options', {'classes': 'collapse', 'fields': ('enable_comments', 'registration_required', 'template_name')}),
        ),
        list_filter = ('sites',),
        search_fields = ('url', 'title'),
    )

    def __repr__(self):
        return "%s -- %s" % (self.url, self.title)

    def get_absolute_url(self):
        return self.url
