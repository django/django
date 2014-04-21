from django.contrib.admin import ModelAdmin
from django.contrib.admin.templatetags.admin_static import static
from django.contrib.postgres import fields, forms
from django.forms import Media
from django.utils.html import format_html


class AdminSplitArrayWidget(forms.SplitArrayWidget):

    def __init__(self, widget, size, extendible=False, **kwargs):
        self.extendible = extendible
        super(AdminSplitArrayWidget, self).__init__(widget, size, **kwargs)

    @property
    def media(self):
        return self.widget.media + Media(
            css={'all': (static('admin/postgres/css/array.css'),)},
            js=[static('admin/postgres/js/Array.js')],
        )

    def format_output(self, rendered_widgets):
        html_string = '<div class="arrayfield">'
        for widget in rendered_widgets:
            html_string += '<div class="arrayfield-inner">'
            html_string += widget
            html_string += '</div>'
        if self.extendible:
            html_string += '<a class="addlink">Add</a>'
        html_string += '</div>'
        return format_html(html_string)


class PostgresModelAdmin(ModelAdmin):
    default_array_size = 3

    def formfield_for_dbfield(self, db_field, **kwargs):
        if isinstance(db_field, fields.ArrayField):
            base_field = self.formfield_for_dbfield(db_field.base_field, **kwargs)
            size = db_field.size or self.default_array_size
            widget = AdminSplitArrayWidget(base_field.widget, size, extendible=not db_field.size)
            if db_field.size:
                return forms.SplitArrayField(base_field, size, widget=widget)
            return forms.SplitArrayField(base_field, size=size, remove_trailing_nulls=True, widget=widget)
        return super(PostgresModelAdmin, self).formfield_for_dbfield(db_field, **kwargs)
