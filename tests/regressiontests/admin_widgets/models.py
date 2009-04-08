
from django.conf import settings
from django.db import models
from django.core.files.storage import default_storage
from django.contrib.auth.models import User

class MyFileField(models.FileField): 
    pass 

class Member(models.Model):
    name = models.CharField(max_length=100)
    birthdate = models.DateTimeField(blank=True, null=True)
    gender = models.CharField(max_length=1, blank=True, choices=[('M','Male'), ('F', 'Female')])

    def __unicode__(self):
        return self.name

class Band(models.Model):
    name = models.CharField(max_length=100)
    members = models.ManyToManyField(Member)

    def __unicode__(self):
        return self.name

class Album(models.Model):
    band = models.ForeignKey(Band)
    name = models.CharField(max_length=100)
    cover_art = models.FileField(upload_to='albums')
    backside_art = MyFileField(upload_to='albums_back', null=True)

    def __unicode__(self):
        return self.name

class HiddenInventoryManager(models.Manager):
    def get_query_set(self):
        return super(HiddenInventoryManager, self).get_query_set().filter(hidden=False)

class Inventory(models.Model):
   barcode = models.PositiveIntegerField(unique=True)
   parent = models.ForeignKey('self', to_field='barcode', blank=True, null=True)
   name = models.CharField(blank=False, max_length=20)
   hidden = models.BooleanField(default=False)

   # see #9258
   default_manager = models.Manager()
   objects = HiddenInventoryManager()

   def __unicode__(self):
      return self.name

class Event(models.Model):
    band = models.ForeignKey(Band)
    start_date = models.DateField(blank=True, null=True)
    start_time = models.TimeField(blank=True, null=True)
    description = models.TextField(blank=True)
    link = models.URLField(blank=True)
    min_age = models.IntegerField(blank=True, null=True)

class Car(models.Model):
    owner = models.ForeignKey(User)
    make = models.CharField(max_length=30)
    model = models.CharField(max_length=30)

    def __unicode__(self):
        return u"%s %s" % (self.make, self.model)

class CarTire(models.Model):
    """
    A single car tire. This to test that a user can only select their own cars.
    """
    car = models.ForeignKey(Car)

__test__ = {'WIDGETS_TESTS': """
>>> from datetime import datetime
>>> from django.utils.html import escape, conditional_escape
>>> from django.core.files.uploadedfile import SimpleUploadedFile
>>> from django.contrib.admin.widgets import FilteredSelectMultiple, AdminSplitDateTime
>>> from django.contrib.admin.widgets import AdminFileWidget, ForeignKeyRawIdWidget, ManyToManyRawIdWidget
>>> from django.contrib.admin.widgets import RelatedFieldWidgetWrapper

Calling conditional_escape on the output of widget.render will simulate what
happens in the template. This is easier than setting up a template and context
for each test.

Make sure that the Admin widgets render properly, that is, without their extra
HTML escaped.

>>> w = FilteredSelectMultiple('test', False)
>>> print conditional_escape(w.render('test', 'test'))
<select multiple="multiple" name="test">
</select><script type="text/javascript">addEvent(window, "load", function(e) {SelectFilter.init("id_test", "test", 0, "%(ADMIN_MEDIA_PREFIX)s"); });</script>
<BLANKLINE>

>>> w = AdminSplitDateTime()
>>> print conditional_escape(w.render('test', datetime(2007, 12, 1, 9, 30)))
<p class="datetime">Date: <input value="2007-12-01" type="text" class="vDateField" name="test_0" size="10" /><br />Time: <input value="09:30:00" type="text" class="vTimeField" name="test_1" size="8" /></p>

>>> band = Band.objects.create(pk=1, name='Linkin Park')
>>> album = band.album_set.create(name='Hybrid Theory', cover_art=r'albums\hybrid_theory.jpg')

>>> w = AdminFileWidget()
>>> print conditional_escape(w.render('test', album.cover_art))
Currently: <a target="_blank" href="%(STORAGE_URL)salbums/hybrid_theory.jpg">albums\hybrid_theory.jpg</a> <br />Change: <input type="file" name="test" />
>>> print conditional_escape(w.render('test', SimpleUploadedFile('test', 'content')))
<input type="file" name="test" />

>>> rel = Album._meta.get_field('band').rel
>>> w = ForeignKeyRawIdWidget(rel)
>>> print conditional_escape(w.render('test', band.pk, attrs={}))
<input type="text" name="test" value="1" class="vForeignKeyRawIdAdminField" /><a href="../../../admin_widgets/band/?t=id" class="related-lookup" id="lookup_id_test" onclick="return showRelatedObjectLookupPopup(this);"> <img src="%(ADMIN_MEDIA_PREFIX)simg/admin/selector-search.gif" width="16" height="16" alt="Lookup" /></a>&nbsp;<strong>Linkin Park</strong>

>>> m1 = Member.objects.create(pk=1, name='Chester')
>>> m2 = Member.objects.create(pk=2, name='Mike')
>>> band.members.add(m1, m2)

>>> rel = Band._meta.get_field('members').rel
>>> w = ManyToManyRawIdWidget(rel)
>>> print conditional_escape(w.render('test', [m1.pk, m2.pk], attrs={}))
<input type="text" name="test" value="1,2" class="vManyToManyRawIdAdminField" /><a href="../../../admin_widgets/member/" class="related-lookup" id="lookup_id_test" onclick="return showRelatedObjectLookupPopup(this);"> <img src="%(ADMIN_MEDIA_PREFIX)simg/admin/selector-search.gif" width="16" height="16" alt="Lookup" /></a>
>>> w._has_changed(None, None)
False
>>> w._has_changed([], None)
False
>>> w._has_changed(None, [u'1'])
True
>>> w._has_changed([1, 2], [u'1', u'2'])
False
>>> w._has_changed([1, 2], [u'1'])
True
>>> w._has_changed([1, 2], [u'1', u'3'])
True

# Check that ForeignKeyRawIdWidget works with fields which aren't related to
# the model's primary key.
>>> apple = Inventory.objects.create(barcode=86, name='Apple')
>>> pear = Inventory.objects.create(barcode=22, name='Pear')
>>> core = Inventory.objects.create(barcode=87, name='Core', parent=apple)
>>> rel = Inventory._meta.get_field('parent').rel
>>> w = ForeignKeyRawIdWidget(rel)
>>> print w.render('test', core.parent_id, attrs={})
<input type="text" name="test" value="86" class="vForeignKeyRawIdAdminField" /><a href="../../../admin_widgets/inventory/?t=barcode" class="related-lookup" id="lookup_id_test" onclick="return showRelatedObjectLookupPopup(this);"> <img src="%(ADMIN_MEDIA_PREFIX)simg/admin/selector-search.gif" width="16" height="16" alt="Lookup" /></a>&nbsp;<strong>Apple</strong>

# see #9258
>>> hidden = Inventory.objects.create(barcode=93, name='Hidden', hidden=True)
>>> child_of_hidden = Inventory.objects.create(barcode=94, name='Child of hidden', parent=hidden)
>>> print w.render('test', child_of_hidden.parent_id, attrs={})
<input type="text" name="test" value="93" class="vForeignKeyRawIdAdminField" /><a href="../../../admin_widgets/inventory/?t=barcode" class="related-lookup" id="lookup_id_test" onclick="return showRelatedObjectLookupPopup(this);"> <img src="%(ADMIN_MEDIA_PREFIX)simg/admin/selector-search.gif" width="16" height="16" alt="Lookup" /></a>&nbsp;<strong>Hidden</strong>
""" % {
    'ADMIN_MEDIA_PREFIX': settings.ADMIN_MEDIA_PREFIX,
    'STORAGE_URL': default_storage.url(''),
}}
