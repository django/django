import re

from django.core.exceptions import ValidationError
from django.forms.utils import RenderableFieldMixin, pretty_name
from django.forms.widgets import MultiWidget, Textarea, TextInput
from django.utils.functional import cached_property
from django.utils.html import format_html, html_safe
from django.utils.translation import gettext_lazy as _

__all__ = ("BoundField",)


class BoundField(RenderableFieldMixin):
    "A Field plus data"

    def __init__(self, form, field, name):
        self.form = form
        self.field = field
        self.name = name
        self.html_name = form.add_prefix(name)
        self.html_initial_name = form.add_initial_prefix(name)
        self.html_initial_id = form.add_initial_prefix(self.auto_id)
        if self.field.label is None:
            self.label = pretty_name(name)
        else:
            self.label = self.field.label
        self.help_text = field.help_text or ""
        self.renderer = form.renderer

    @cached_property
    def subwidgets(self):
        """
        Most widgets yield a single subwidget, but others like RadioSelect and
        CheckboxSelectMultiple produce one subwidget for each choice.

        This property is cached so that only one database query occurs when
        rendering ModelChoiceFields.
        """
        id_ = self.field.widget.attrs.get("id") or self.auto_id
        attrs = {"id": id_} if id_ else {}
        attrs = self.build_widget_attrs(attrs)
        return [
            BoundWidget(self.field.widget, widget, self.form.renderer)
            for widget in self.field.widget.subwidgets(
                self.html_name, self.value(), attrs=attrs
            )
        ]

    def __bool__(self):
        # BoundField evaluates to True even if it doesn't have subwidgets.
        return True

    def __iter__(self):
        return iter(self.subwidgets)

    def __len__(self):
        return len(self.subwidgets)

    def __getitem__(self, idx):
        # Prevent unnecessary reevaluation when accessing BoundField's attrs
        # from templates.
        if not isinstance(idx, (int, slice)):
            raise TypeError(
                "BoundField indices must be integers or slices, not %s."
                % type(idx).__name__
            )
        return self.subwidgets[idx]

    @property
    def errors(self):
        """
        Return an ErrorList (empty if there are no errors) for this field.
        """
        return self.form.errors.get(
            self.name, self.form.error_class(renderer=self.form.renderer)
        )

    @property
    def template_name(self):
        return self.field.template_name or self.form.renderer.field_template_name

    def get_context(self):
        return {"field": self}

    def as_widget(self, widget=None, attrs=None, only_initial=False):
        """
        Render the field by rendering the passed widget, adding any HTML
        attributes passed as attrs. If a widget isn't specified, use the
        field's default widget.
        """
        widget = widget or self.field.widget
        if self.field.localize:
            widget.is_localized = True
        attrs = attrs or {}
        attrs = self.build_widget_attrs(attrs, widget)
        if self.auto_id and "id" not in widget.attrs:
            attrs.setdefault(
                "id", self.html_initial_id if only_initial else self.auto_id
            )
        if only_initial and self.html_initial_name in self.form.data:
            # Propagate the hidden initial value.
            value = self.form._widget_data_value(
                self.field.hidden_widget(),
                self.html_initial_name,
            )
        else:
            value = self.value()
        return widget.render(
            name=self.html_initial_name if only_initial else self.html_name,
            value=value,
            attrs=attrs,
            renderer=self.form.renderer,
        )

    def as_text(self, attrs=None, **kwargs):
        """
        Return a string of HTML for representing this as an <input type="text">.
        """
        return self.as_widget(TextInput(), attrs, **kwargs)

    def as_textarea(self, attrs=None, **kwargs):
        """Return a string of HTML for representing this as a <textarea>."""
        return self.as_widget(Textarea(), attrs, **kwargs)

    def as_hidden(self, attrs=None, **kwargs):
        """
        Return a string of HTML for representing this as an <input type="hidden">.
        """
        return self.as_widget(self.field.hidden_widget(), attrs, **kwargs)

    @property
    def data(self):
        """
        Return the data for this BoundField, or None if it wasn't given.
        """
        return self.form._widget_data_value(self.field.widget, self.html_name)

    def value(self):
        """
        Return the value for this BoundField, using the initial value if
        the form is not bound or the data otherwise.
        """
        data = self.initial
        if self.form.is_bound:
            data = self.field.bound_data(self.data, data)
        return self.field.prepare_value(data)

    def _has_changed(self):
        field = self.field
        if field.show_hidden_initial:
            hidden_widget = field.hidden_widget()
            initial_value = self.form._widget_data_value(
                hidden_widget,
                self.html_initial_name,
            )
            try:
                initial_value = field.to_python(initial_value)
            except ValidationError:
                # Always assume data has changed if validation fails.
                return True
        else:
            initial_value = self.initial
        return field.has_changed(initial_value, self.data)

    def label_tag(self, contents=None, attrs=None, label_suffix=None, tag=None):
        """
        Wrap the given contents in a <label>, if the field has an ID attribute.
        contents should be mark_safe'd to avoid HTML escaping. If contents
        aren't given, use the field's HTML-escaped label.

        If attrs are given, use them as HTML attributes on the <label> tag.

        label_suffix overrides the form's label_suffix.
        """
        contents = contents or self.label
        if label_suffix is None:
            label_suffix = (
                self.field.label_suffix
                if self.field.label_suffix is not None
                else self.form.label_suffix
            )
        # Only add the suffix if the label does not end in punctuation.
        # Translators: If found as last label character, these punctuation
        # characters will prevent the default label_suffix to be appended to the label
        if label_suffix and contents and contents[-1] not in _(":?.!"):
            contents = format_html("{}{}", contents, label_suffix)
        widget = self.field.widget
        id_ = widget.attrs.get("id") or self.auto_id
        if id_:
            id_for_label = widget.id_for_label(id_)
            if id_for_label:
                attrs = {**(attrs or {}), "for": id_for_label}
            if self.field.required and hasattr(self.form, "required_css_class"):
                attrs = attrs or {}
                if "class" in attrs:
                    attrs["class"] += " " + self.form.required_css_class
                else:
                    attrs["class"] = self.form.required_css_class
        context = {
            "field": self,
            "label": contents,
            "attrs": attrs,
            "use_tag": bool(id_),
            "tag": tag or "label",
        }
        return self.form.render(self.form.template_name_label, context)

    def legend_tag(self, contents=None, attrs=None, label_suffix=None):
        """
        Wrap the given contents in a <legend>, if the field has an ID
        attribute. Contents should be mark_safe'd to avoid HTML escaping. If
        contents aren't given, use the field's HTML-escaped label.

        If attrs are given, use them as HTML attributes on the <legend> tag.

        label_suffix overrides the form's label_suffix.
        """
        return self.label_tag(contents, attrs, label_suffix, tag="legend")

    def css_classes(self, extra_classes=None):
        """
        Return a string of space-separated CSS classes for this field.
        """
        if hasattr(extra_classes, "split"):
            extra_classes = extra_classes.split()
        extra_classes = set(extra_classes or [])
        if self.errors and hasattr(self.form, "error_css_class"):
            extra_classes.add(self.form.error_css_class)
        if self.field.required and hasattr(self.form, "required_css_class"):
            extra_classes.add(self.form.required_css_class)
        return " ".join(extra_classes)

    @property
    def is_hidden(self):
        """Return True if this BoundField's widget is hidden."""
        return self.field.widget.is_hidden

    @property
    def auto_id(self):
        """
        Calculate and return the ID attribute for this BoundField, if the
        associated Form has specified auto_id. Return an empty string otherwise.
        """
        auto_id = self.form.auto_id  # Boolean or string
        if auto_id and "%s" in str(auto_id):
            return auto_id % self.html_name
        elif auto_id:
            return self.html_name
        return ""

    @property
    def id_for_label(self):
        """
        Wrapper around the field widget's `id_for_label` method.
        Useful, for example, for focusing on this field regardless of whether
        it has a single widget or a MultiWidget.
        """
        widget = self.field.widget
        id_ = widget.attrs.get("id") or self.auto_id
        return widget.id_for_label(id_)

    @cached_property
    def initial(self):
        return self.form.get_initial_for_field(self.field, self.name)

    def build_widget_attrs(self, attrs, widget=None):
        widget = widget or self.field.widget
        attrs = dict(attrs)  # Copy attrs to avoid modifying the argument.
        if (
            widget.use_required_attribute(self.initial)
            and self.field.required
            and self.form.use_required_attribute
        ):
            # MultiValueField has require_all_fields: if False, fall back
            # on subfields.
            if (
                hasattr(self.field, "require_all_fields")
                and not self.field.require_all_fields
                and isinstance(self.field.widget, MultiWidget)
            ):
                for subfield, subwidget in zip(self.field.fields, widget.widgets):
                    subwidget.attrs["required"] = (
                        subwidget.use_required_attribute(self.initial)
                        and subfield.required
                    )
            else:
                attrs["required"] = True
        if self.field.disabled:
            attrs["disabled"] = True
        if not widget.is_hidden and self.errors:
            attrs["aria-invalid"] = "true"
        # If a custom aria-describedby attribute is given (either via the attrs
        # argument or widget.attrs) and help_text is used, the custom
        # aria-described by is preserved so user can set the desired order.
        if (
            not attrs.get("aria-describedby")
            and not widget.attrs.get("aria-describedby")
            and self.field.help_text
            and not self.use_fieldset
            and self.auto_id
        ):
            attrs["aria-describedby"] = f"{self.auto_id}_helptext"
        return attrs

    @property
    def widget_type(self):
        return re.sub(
            r"widget$|input$", "", self.field.widget.__class__.__name__.lower()
        )

    @property
    def use_fieldset(self):
        """
        Return the value of this BoundField widget's use_fieldset attribute.
        """
        return self.field.widget.use_fieldset


@html_safe
class BoundWidget:
    """
    A container class used for iterating over widgets. This is useful for
    widgets that have choices. For example, the following can be used in a
    template:

    {% for radio in myform.beatles %}
      <label for="{{ radio.id_for_label }}">
        {{ radio.choice_label }}
        <span class="radio">{{ radio.tag }}</span>
      </label>
    {% endfor %}
    """

    def __init__(self, parent_widget, data, renderer):
        self.parent_widget = parent_widget
        self.data = data
        self.renderer = renderer

    def __str__(self):
        return self.tag(wrap_label=True)

    def tag(self, wrap_label=False):
        context = {"widget": {**self.data, "wrap_label": wrap_label}}
        return self.parent_widget._render(self.template_name, context, self.renderer)

    @property
    def template_name(self):
        if "template_name" in self.data:
            return self.data["template_name"]
        return self.parent_widget.template_name

    @property
    def id_for_label(self):
        return self.data["attrs"].get("id")

    @property
    def choice_label(self):
        return self.data["label"]
