from django.contrib.contenttypes.models import ContentType
from django.db import models
from django.forms import ModelForm, modelformset_factory
from django.forms.models import BaseModelFormSet


class BaseGenericInlineFormSet(BaseModelFormSet):
    """
    A formset for generic inline objects to a parent.
    """

    def __init__(
        self,
        data=None,
        files=None,
        instance=None,
        save_as_new=False,
        prefix=None,
        queryset=None,
        **kwargs,
    ):
        opts = self.model._meta
        self.instance = instance
        self.rel_name = (
            opts.app_label
            + "-"
            + opts.model_name
            + "-"
            + self.ct_field.name
            + "-"
            + self.ct_fk_field.name
        )
        self.save_as_new = save_as_new
        if self.instance is None or self.instance.pk is None:
            qs = self.model._default_manager.none()
        else:
            if queryset is None:
                queryset = self.model._default_manager
            qs = queryset.filter(
                **{
                    self.ct_field.name: ContentType.objects.get_for_model(
                        self.instance, for_concrete_model=self.for_concrete_model
                    ),
                    self.ct_fk_field.name: self.instance.pk,
                }
            )
        super().__init__(queryset=qs, data=data, files=files, prefix=prefix, **kwargs)

    def initial_form_count(self):
        if self.save_as_new:
            return 0
        return super().initial_form_count()

    @classmethod
    def get_default_prefix(cls):
        opts = cls.model._meta
        return (
            opts.app_label
            + "-"
            + opts.model_name
            + "-"
            + cls.ct_field.name
            + "-"
            + cls.ct_fk_field.name
        )

    def save_new(self, form, commit=True):
        setattr(
            form.instance,
            self.ct_field.attname,
            ContentType.objects.get_for_model(self.instance).pk,
        )
        setattr(form.instance, self.ct_fk_field.attname, self.instance.pk)
        return form.save(commit=commit)


def generic_inlineformset_factory(
    model,
    form=ModelForm,
    formset=BaseGenericInlineFormSet,
    ct_field="content_type",
    fk_field="object_id",
    fields=None,
    exclude=None,
    extra=3,
    can_order=False,
    can_delete=True,
    max_num=None,
    formfield_callback=None,
    validate_max=False,
    for_concrete_model=True,
    min_num=None,
    validate_min=False,
    absolute_max=None,
    can_delete_extra=True,
):
    """
    Return a ``GenericInlineFormSet`` for the given kwargs.

    You must provide ``ct_field`` and ``fk_field`` if they are different from
    the defaults ``content_type`` and ``object_id`` respectively.
    """
    opts = model._meta
    # if there is no field called `ct_field` let the exception propagate
    ct_field = opts.get_field(ct_field)
    if (
        not isinstance(ct_field, models.ForeignKey)
        or ct_field.remote_field.model != ContentType
    ):
        raise Exception("fk_name '%s' is not a ForeignKey to ContentType" % ct_field)
    fk_field = opts.get_field(fk_field)  # let the exception propagate
    exclude = [*(exclude or []), ct_field.name, fk_field.name]
    FormSet = modelformset_factory(
        model,
        form=form,
        formfield_callback=formfield_callback,
        formset=formset,
        extra=extra,
        can_delete=can_delete,
        can_order=can_order,
        fields=fields,
        exclude=exclude,
        max_num=max_num,
        validate_max=validate_max,
        min_num=min_num,
        validate_min=validate_min,
        absolute_max=absolute_max,
        can_delete_extra=can_delete_extra,
    )
    FormSet.ct_field = ct_field
    FormSet.ct_fk_field = fk_field
    FormSet.for_concrete_model = for_concrete_model
    return FormSet
