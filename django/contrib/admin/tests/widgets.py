"""
>>> from datetime import datetime
>>> from django.utils.html import escape, conditional_escape
>>> from django.contrib.admin.widgets import FilteredSelectMultiple, AdminSplitDateTime
>>> from django.contrib.admin.widgets import AdminFileWidget, ForeignKeyRawIdWidget
>>> from django.contrib.admin.widgets import RelatedFieldWidgetWrapper
>>> from django.contrib.admin.models import LogEntry

Calling conditional_escape on the output of widget.render will simulate what
happens in the template. This is easier than setting up a template and context
for each test.

Make sure that the Admin widgets render properly, that is, without their extra
HTML escaped.

>>> w = FilteredSelectMultiple('test', False)
>>> print conditional_escape(w.render('test', 'test'))
<select multiple="multiple" name="test">
</select><script type="text/javascript">addEvent(window, "load", function(e) {SelectFilter.init("id_test", "test", 0, "/media/"); });</script>
<BLANKLINE>

>>> w = AdminSplitDateTime()
>>> print conditional_escape(w.render('test', datetime(2007, 12, 1, 9, 30)))
<p class="datetime">Date: <input value="2007-12-01" type="text" class="vDateField" name="test_0" size="10" /><br />Time: <input value="09:30:00" type="text" class="vTimeField" name="test_1" size="8" /></p>

>>> w = AdminFileWidget()
>>> print conditional_escape(w.render('test', 'test'))
Currently: <a target="_blank" href="test">test</a> <br>Change: <input type="file" name="test" />

>>> rel = LogEntry._meta.get_field('user').rel
>>> w = ForeignKeyRawIdWidget(rel)
>>> print conditional_escape(w.render('test', 'test', attrs={}))
<input type="text" name="test" value="test" class="vForeignKeyRawIdAdminField" /><a href="../../../auth/user/" class="related-lookup" id="lookup_id_test" onclick="return showRelatedObjectLookupPopup(this);"> <img src="/media/img/admin/selector-search.gif" width="16" height="16" alt="Lookup"></a>

"""
