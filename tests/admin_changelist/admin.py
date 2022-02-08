from django.contrib import admin
from django.contrib.auth.admin import UserAdmin
from django.contrib.auth.models import User
from django.core.paginator import Paginator

from .models import Band, Child, Event, Parent, Swallow

site = admin.AdminSite(name="admin")

site.register(User, UserAdmin)


class CustomPaginator(Paginator):
    def __init__(self, queryset, page_size, orphans=0, allow_empty_first_page=True):
        super().__init__(
            queryset, 5, orphans=2, allow_empty_first_page=allow_empty_first_page
        )


class EventAdmin(admin.ModelAdmin):
    date_hierarchy = "date"
    list_display = ["event_date_func"]

    @admin.display
    def event_date_func(self, event):
        return event.date

    def has_add_permission(self, request):
        return False


site.register(Event, EventAdmin)


class ParentAdmin(admin.ModelAdmin):
    list_filter = ["child__name"]
    search_fields = ["child__name"]
    list_select_related = ["child"]


class ChildAdmin(admin.ModelAdmin):
    list_display = ["name", "parent"]
    list_per_page = 10
    list_filter = ["parent", "age"]

    def get_queryset(self, request):
        return super().get_queryset(request).select_related("parent")


class CustomPaginationAdmin(ChildAdmin):
    paginator = CustomPaginator


class FilteredChildAdmin(admin.ModelAdmin):
    list_display = ["name", "parent"]
    list_per_page = 10

    def get_queryset(self, request):
        return super().get_queryset(request).filter(name__contains="filtered")


class BandAdmin(admin.ModelAdmin):
    list_filter = ["genres"]


class NrOfMembersFilter(admin.SimpleListFilter):
    title = "number of members"
    parameter_name = "nr_of_members_partition"

    def lookups(self, request, model_admin):
        return [
            ("5", "0 - 5"),
            ("more", "more than 5"),
        ]

    def queryset(self, request, queryset):
        value = self.value()
        if value == "5":
            return queryset.filter(nr_of_members__lte=5)
        if value == "more":
            return queryset.filter(nr_of_members__gt=5)


class BandCallableFilterAdmin(admin.ModelAdmin):
    list_filter = [NrOfMembersFilter]


site.register(Band, BandCallableFilterAdmin)


class GroupAdmin(admin.ModelAdmin):
    list_filter = ["members"]


class ConcertAdmin(admin.ModelAdmin):
    list_filter = ["group__members"]
    search_fields = ["group__members__name"]


class QuartetAdmin(admin.ModelAdmin):
    list_filter = ["members"]


class ChordsBandAdmin(admin.ModelAdmin):
    list_filter = ["members"]


class InvitationAdmin(admin.ModelAdmin):
    list_display = ("band", "player")
    list_select_related = ("player",)


class DynamicListDisplayChildAdmin(admin.ModelAdmin):
    list_display = ("parent", "name", "age")

    def get_list_display(self, request):
        my_list_display = super().get_list_display(request)
        if request.user.username == "noparents":
            my_list_display = list(my_list_display)
            my_list_display.remove("parent")
        return my_list_display


class DynamicListDisplayLinksChildAdmin(admin.ModelAdmin):
    list_display = ("parent", "name", "age")
    list_display_links = ["parent", "name"]

    def get_list_display_links(self, request, list_display):
        return ["age"]


site.register(Child, DynamicListDisplayChildAdmin)


class NoListDisplayLinksParentAdmin(admin.ModelAdmin):
    list_display_links = None
    list_display = ["name"]
    list_editable = ["name"]
    actions_on_bottom = True


site.register(Parent, NoListDisplayLinksParentAdmin)


class SwallowAdmin(admin.ModelAdmin):
    actions = None  # prevent ['action_checkbox'] + list(list_display)
    list_display = ("origin", "load", "speed", "swallowonetoone")
    list_editable = ["load", "speed"]
    list_per_page = 3


site.register(Swallow, SwallowAdmin)


class DynamicListFilterChildAdmin(admin.ModelAdmin):
    list_filter = ("parent", "name", "age")

    def get_list_filter(self, request):
        my_list_filter = super().get_list_filter(request)
        if request.user.username == "noparents":
            my_list_filter = list(my_list_filter)
            my_list_filter.remove("parent")
        return my_list_filter


class DynamicSearchFieldsChildAdmin(admin.ModelAdmin):
    search_fields = ("name",)

    def get_search_fields(self, request):
        search_fields = super().get_search_fields(request)
        search_fields += ("age",)
        return search_fields


class EmptyValueChildAdmin(admin.ModelAdmin):
    empty_value_display = "-empty-"
    list_display = ("name", "age_display", "age")

    @admin.display(empty_value="&dagger;")
    def age_display(self, obj):
        return obj.age
