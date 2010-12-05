from django.contrib.auth.decorators import login_required
from django.core.paginator import Paginator
from django.core.urlresolvers import reverse
from django.utils.decorators import method_decorator
from django.views import generic

from regressiontests.generic_views.models import Artist, Author, Book, Page
from regressiontests.generic_views.forms import AuthorForm


class CustomTemplateView(generic.TemplateView):
    template_name = 'generic_views/about.html'

    def get_context_data(self, **kwargs):
        return {
            'params': kwargs,
            'key': 'value'
        }


class ObjectDetail(generic.DetailView):
    template_name = 'generic_views/detail.html'

    def get_object(self):
        return {'foo': 'bar'}


class ArtistDetail(generic.DetailView):
    queryset = Artist.objects.all()


class AuthorDetail(generic.DetailView):
    queryset = Author.objects.all()


class PageDetail(generic.DetailView):
    queryset = Page.objects.all()
    template_name_field = 'template'


class DictList(generic.ListView):
    """A ListView that doesn't use a model."""
    queryset = [
        {'first': 'John', 'last': 'Lennon'},
        {'last': 'Yoko',  'last': 'Ono'}
    ]
    template_name = 'generic_views/list.html'


class AuthorList(generic.ListView):
    queryset = Author.objects.all()


class CustomPaginator(Paginator):
    def __init__(self, queryset, page_size, orphans=0, allow_empty_first_page=True):
        super(CustomPaginator, self).__init__(
            queryset,
            page_size,
            orphans=2,
            allow_empty_first_page=allow_empty_first_page)

class AuthorListCustomPaginator(AuthorList):
    paginate_by = 5;

    def get_paginator(self, queryset, page_size, orphans=0, allow_empty_first_page=True):
        return super(AuthorListCustomPaginator, self).get_paginator(
            queryset,
            page_size,
            orphans=2,
            allow_empty_first_page=allow_empty_first_page)

class ArtistCreate(generic.CreateView):
    model = Artist


class NaiveAuthorCreate(generic.CreateView):
    queryset = Author.objects.all()


class AuthorCreate(generic.CreateView):
    model = Author
    success_url = '/list/authors/'


class SpecializedAuthorCreate(generic.CreateView):
    model = Author
    form_class = AuthorForm
    template_name = 'generic_views/form.html'
    context_object_name = 'thingy'

    def get_success_url(self):
        return reverse('author_detail', args=[self.object.id,])


class AuthorCreateRestricted(AuthorCreate):
    post = method_decorator(login_required)(AuthorCreate.post)


class ArtistUpdate(generic.UpdateView):
    model = Artist


class NaiveAuthorUpdate(generic.UpdateView):
    queryset = Author.objects.all()


class AuthorUpdate(generic.UpdateView):
    model = Author
    success_url = '/list/authors/'


class SpecializedAuthorUpdate(generic.UpdateView):
    model = Author
    form_class = AuthorForm
    template_name = 'generic_views/form.html'
    context_object_name = 'thingy'

    def get_success_url(self):
        return reverse('author_detail', args=[self.object.id,])


class NaiveAuthorDelete(generic.DeleteView):
    queryset = Author.objects.all()


class AuthorDelete(generic.DeleteView):
    model = Author
    success_url = '/list/authors/'


class SpecializedAuthorDelete(generic.DeleteView):
    queryset = Author.objects.all()
    template_name = 'generic_views/confirm_delete.html'
    context_object_name = 'thingy'

    def get_success_url(self):
        return reverse('authors_list')


class BookConfig(object):
    queryset = Book.objects.all()
    date_field = 'pubdate'

class BookArchive(BookConfig, generic.ArchiveIndexView):
    pass

class BookYearArchive(BookConfig, generic.YearArchiveView):
    pass

class BookMonthArchive(BookConfig, generic.MonthArchiveView):
    pass

class BookWeekArchive(BookConfig, generic.WeekArchiveView):
    pass

class BookDayArchive(BookConfig, generic.DayArchiveView):
    pass

class BookTodayArchive(BookConfig, generic.TodayArchiveView):
    pass

class BookDetail(BookConfig, generic.DateDetailView):
    pass

class AuthorGetQuerySetFormView(generic.edit.ModelFormMixin):
    def get_queryset(self):
        return Author.objects.all()
