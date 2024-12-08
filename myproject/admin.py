from django.contrib import admin
from django.forms import ModelForm
from django.contrib.admin.widgets import FilteredSelectMultiple
from .models import ParentModel, ChildModel

class ChildModelForm(ModelForm):
    class Meta:
        model = ChildModel
        fields = '__all__'
        widgets = {
            'related_field': FilteredSelectMultiple('Related Items', False),
        }

class ChildInline(admin.TabularInline):
    model = ChildModel
    form = ChildModelForm
    extra = 1

class ParentModelAdmin(admin.ModelAdmin):
    inlines = [ChildInline]

admin.site.register(ParentModel, ParentModelAdmin)
