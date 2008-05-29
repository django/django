
from django.conf import settings
from django.db import models

class Member(models.Model):
    name = models.CharField(max_length=100)
    
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
    
    def __unicode__(self):
        return self.name

__test__ = {'WIDGETS_TESTS': """
>>> from datetime import datetime
>>> from django.utils.html import escape, conditional_escape
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

>>> w = AdminFileWidget()
>>> print conditional_escape(w.render('test', 'test'))
Currently: <a target="_blank" href="%(MEDIA_URL)stest">test</a> <br />Change: <input type="file" name="test" />

>>> band = Band.objects.create(pk=1, name='Linkin Park')
>>> album = band.album_set.create(name='Hybrid Theory')

>>> rel = Album._meta.get_field('band').rel
>>> w = ForeignKeyRawIdWidget(rel)
>>> print conditional_escape(w.render('test', band.pk, attrs={}))
<input type="text" name="test" value="1" class="vForeignKeyRawIdAdminField" /><a href="../../../admin_widgets/band/" class="related-lookup" id="lookup_id_test" onclick="return showRelatedObjectLookupPopup(this);"> <img src="%(ADMIN_MEDIA_PREFIX)simg/admin/selector-search.gif" width="16" height="16" alt="Lookup" /></a>&nbsp;<strong>Linkin Park</strong>

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

""" % {
    'ADMIN_MEDIA_PREFIX': settings.ADMIN_MEDIA_PREFIX,
    'MEDIA_URL': settings.MEDIA_URL,
}}
