"""
Form Widget classes specific to the Django admin site.
"""

from django import newforms as forms
import datetime

class FilteredSelectMultiple(forms.SelectMultiple):
    """
    A SelectMultiple with a JavaScript filter interface.

    Note that the resulting JavaScript assumes that the SelectFilter2.js
    library and its dependencies have been loaded in the HTML page.
    """
    def __init__(self, verbose_name, is_stacked, attrs=None, choices=()):
        self.verbose_name = verbose_name
        self.is_stacked = is_stacked
        super(FilteredSelectMultiple, self).__init__(attrs, choices)

    def render(self, name, value, attrs=None, choices=()):
        from django.conf import settings
        output = [super(FilteredSelectMultiple, self).render(name, value, attrs, choices)]
        output.append(u'<script type="text/javascript">addEvent(window, "load", function(e) {')
        # TODO: "id_" is hard-coded here. This should instead use the correct
        # API to determine the ID dynamically.
        output.append(u'SelectFilter.init("id_%s", "%s", %s, "%s"); });</script>\n' % \
            (name, self.verbose_name.replace('"', '\\"'), int(self.is_stacked), settings.ADMIN_MEDIA_PREFIX))
        return u''.join(output)

class AdminSplitDateTime(forms.SplitDateTimeWidget):
    """
    A SplitDateTime Widget that has some admin-specific styling.
    """
    def __init__(self, attrs=None):
        widgets = [forms.TextInput(attrs={'class': 'vDateField', 'size': '10'}),
                   forms.TextInput(attrs={'class': 'vTimeField', 'size': '8'})]
        # Note that we're calling MultiWidget, not SplitDateTimeWidget, because
        # we want to define widgets.
        forms.MultiWidget.__init__(self, widgets, attrs)

    def format_output(self, rendered_widgets):
        return u'<p class="datetime">%s %s<br />%s %s</p>' % \
            (_('Date:'), rendered_widgets[0], _('Time:'), rendered_widgets[1])
