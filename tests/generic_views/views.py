from __future__ import absolute_import

from django.contrib.auth.decorators import login_required
from django.core.paginator import Paginator
from django.core.urlresolvers import reverse, reverse_lazy
from django.utils.decorators import method_decorator
from django.views import generic

from .test_forms import AuthorForm, ContactForm
from .models import Artist, Author, Book, Page, BookSigning


class CustomTemplateView(generic.TemplateView):
    template_name = 'generic_views/about.html'

    def get_context_data(self, **kwargs):
        context = super(CustomTemplateView, self).get_context_data(**kwargs)
        context.update({'key': 'value'})
        return context


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
        {'first': 'Yoko',  'last': 'Ono'}
    ]
    template_name = 'generic_views/list.html'


class ArtistList(generic.ListView):
    template_name = 'generic_views/list.html'
    queryset = Artist.objects.all()


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
    paginate_by = 5

    def get_paginator(self, queryset, page_size, orphans=0, allow_empty_first_page=True):
        return super(AuthorListCustomPaginator, self).get_paginator(
            queryset,
            page_size,
            orphans=2,
            allow_empty_first_page=allow_empty_first_page)


class ContactView(generic.FormView):
    form_class = ContactForm
    success_url = reverse_lazy('authors_list')
    template_name = 'generic_views/form.html'


class ArtistCreate(generic.CreateView):
    model = Artist
    fields = '__all__'


class NaiveAuthorCreate(generic.CreateView):
    queryset = Author.objects.all()
    fields = '__all__'


class TemplateResponseWithoutTemplate(generic.detail.SingleObjectTemplateResponseMixin, generic.View):
    # we don't define the usual template_name here

    def __init__(self):
        # Dummy object, but attr is required by get_template_name()
        self.object = None


class AuthorCreate(generic.CreateView):
    model = Author
    success_url = '/list/authors/'
    fields = '__all__'


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
    fields = '__all__'


class NaiveAuthorUpdate(generic.UpdateView):
    queryset = Author.objects.all()
    fields = '__all__'


class AuthorUpdate(generic.UpdateView):
    model = Author
    success_url = '/list/authors/'
    fields = '__all__'


class OneAuthorUpdate(generic.UpdateView):
    success_url = '/list/authors/'
    fields = '__all__'

    def get_object(self):
        return Author.objects.get(pk=1)


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
    fields = '__all__'

    def get_queryset(self):
        return Author.objects.all()

class BookDetailGetObjectCustomQueryset(BookDetail):
    def get_object(self, queryset=None):
        return super(BookDetailGetObjectCustomQueryset,self).get_object(
            queryset=Book.objects.filter(pk=2))


class CustomMultipleObjectMixinView(generic.list.MultipleObjectMixin, generic.View):
    queryset = [
        {'name': 'John'},
        {'name': 'Yoko'},
    ]

    def get(self, request):
        self.object_list = self.get_queryset()


class CustomContextView(generic.detail.SingleObjectMixin, generic.View):
    model = Book
    object = Book(name='dummy')

    def get_object(self):
        return Book(name="dummy")

    def get_context_data(self, **kwargs):
        context = {'custom_key': 'custom_value'}
        context.update(kwargs)
        return super(CustomContextView, self).get_context_data(**context)

    def get_context_object_name(self, obj):
        return "test_name"

class CustomSingleObjectView(generic.detail.SingleObjectMixin, generic.View):
    model = Book
    object = Book(name="dummy")

class BookSigningConfig(object):
    model = BookSigning
    date_field = 'event_date'
    # use the same templates as for books
    def get_template_names(self):
        return ['generic_views/book%s.html' % self.template_name_suffix]

class BookSigningArchive(BookSigningConfig, generic.ArchiveIndexView):
    pass

class BookSigningYearArchive(BookSigningConfig, generic.YearArchiveView):
    pass

class BookSigningMonthArchive(BookSigningConfig, generic.MonthArchiveView):
    pass

class BookSigningWeekArchive(BookSigningConfig, generic.WeekArchiveView):
    pass

class BookSigningDayArchive(BookSigningConfig, generic.DayArchiveView):
    pass

class BookSigningTodayArchive(BookSigningConfig, generic.TodayArchiveView):
    pass

class BookSigningDetail(BookSigningConfig, generic.DateDetailView):
    context_object_name = 'book'


class NonModel(object):
    id = "non_model_1"

    _meta = None


class NonModelDetail(generic.DetailView):

    template_name = 'generic_views/detail.html'
    model = NonModel

    def get_object(self, queryset=None):
        return NonModel()
