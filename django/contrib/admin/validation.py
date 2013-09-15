# -*- encoding: utf-8 -*-
from __future__ import unicode_literals


class BaseValidator(object):

    def validate(self, cls, model):
        for m in dir(self):
            if m.startswith('validate_'):
                getattr(self, m)(cls, model)

    def validate_raw_id_fields(self, cls, model):
        pass

    def validate_fields(self, cls, model):
        pass

    def validate_fieldsets(self, cls, model):
        pass

    def validate_exclude(self, cls, model):
        pass

    def validate_form(self, cls, model):
        pass

    def validate_filter_vertical(self, cls, model):
        pass

    def validate_filter_horizontal(self, cls, model):
        pass

    def validate_radio_fields(self, cls, model):
        pass

    def validate_prepopulated_fields(self, cls, model):
        pass

    def validate_ordering(self, cls, model):
        pass

    def validate_readonly_fields(self, cls, model):
        pass


class ModelAdminValidator(BaseValidator):

    def validate_save_as(self, cls, model):
        pass

    def validate_save_on_top(self, cls, model):
        pass

    def validate_inlines(self, cls, model):
        pass

    def validate_list_display(self, cls, model):
        pass

    def validate_list_display_links(self, cls, model):
        pass

    def validate_list_filter(self, cls, model):
        pass

    def validate_list_select_related(self, cls, model):
        pass

    def validate_list_per_page(self, cls, model):
        pass

    def validate_list_max_show_all(self, cls, model):
        pass

    def validate_list_editable(self, cls, model):
        pass

    def validate_search_fields(self, cls, model):
        pass

    def validate_date_hierarchy(self, cls, model):
        pass


class InlineValidator(BaseValidator):

    def validate_fk_name(self, cls, model):
        pass

    def validate_extra(self, cls, model):
        pass

    def validate_max_num(self, cls, model):
        pass

    def validate_formset(self, cls, model):
        pass
