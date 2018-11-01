from django.contrib.auth.decorators import login_required
from django.core.paginator import Paginator
from django.urls import reverse, reverse_lazy
from django.utils.decorators import method_decorator
from django.views import generic

from .forms import AuthorForm, ContactForm
from .models import Artist, Author, Book, BookSigning, Page


class CustomTemplateView(generic.TemplateView):
    template_name = 'generic_views/about.html'

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
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


class AuthorCustomDetail(generic.DetailView):
    template_name = 'generic_views/author_detail.html'
    queryset = Author.objects.all()

    def get(self, request, *args, **kwargs):
        # Ensures get_context_object_name() doesn't reference self.object.
        author = self.get_object()
        context = {'custom_' + self.get_context_object_name(author): author}
        return self.render_to_response(context)


class PageDetail(generic.DetailView):
    queryset = Page.objects.all()
    template_name_field = 'template'


class DictList(generic.ListView):
    """A ListView that doesn't use a model."""
    queryset = [
        {'first': 'John', 'last': 'Lennon'},
        {'first': 'Yoko', 'last': 'Ono'}
    ]
    template_name = 'generic_views/list.html'


class ArtistList(generic.ListView):
    template_name = 'generic_views/list.html'
    queryset = Artist.objects.all()


class AuthorList(generic.ListView):
    queryset = Author.objects.all()


class AuthorListGetQuerysetReturnsNone(AuthorList):
    def get_queryset(self):
        return None


class BookList(generic.ListView):
    model = Book


class CustomPaginator(Paginator):
    def __init__(self, queryset, page_size, orphans=0, allow_empty_first_page=True):
        super().__init__(queryset, page_size, orphans=2, allow_empty_first_page=allow_empty_first_page)


class AuthorListCustomPaginator(AuthorList):
    paginate_by = 5

    def get_paginator(self, queryset, page_size, orphans=0, allow_empty_first_page=True):
        return super().get_paginator(queryset, page_size, orphans=2, allow_empty_first_page=allow_empty_first_page)


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
        return reverse('author_detail', args=[self.object.id])


class AuthorCreateRestricted(AuthorCreate):
    post = method_decorator(login_required)(AuthorCreate.post)


class ArtistUpdate(generic.UpdateView):
    model = Artist
    fields = '__all__'


class NaiveAuthorUpdate(generic.UpdateView):
    queryset = Author.objects.all()
    fields = '__all__'


class AuthorUpdate(generic.UpdateView):
    get_form_called_count = 0  # Used to ensure get_form() is called once.
    model = Author
    success_url = '/list/authors/'
    fields = '__all__'

    def get_form(self, *args, **kwargs):
        self.get_form_called_count += 1
        return super().get_form(*args, **kwargs)


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
        return reverse('author_detail', args=[self.object.id])


class NaiveAuthorDelete(generic.DeleteView):
    queryset = Author.objects.all()


class AuthorDelete(generic.DeleteView):
    model = Author
    success_url = '/list/authors/'


class SpecializedAuthorDelete(generic.DeleteView):
    queryset = Author.objects.all()
    template_name = 'generic_views/confirm_delete.html'
    context_object_name = 'thingy'
    success_url = reverse_lazy('authors_list')


class BookConfig:
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
        return super().get_object(queryset=Book.objects.filter(pk=self.kwargs['pk']))


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
        return super().get_context_data(**context)

    def get_context_object_name(self, obj):
        return "test_name"


class CustomSingleObjectView(generic.detail.SingleObjectMixin, generic.View):
    model = Book
    object = Book(name="dummy")


class BookSigningConfig:
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


class BookArchiveWithoutDateField(generic.ArchiveIndexView):
    queryset = Book.objects.all()


class BookSigningDetail(BookSigningConfig, generic.DateDetailView):
    context_object_name = 'book'


class NonModel:
    id = "non_model_1"

    _meta = None


class NonModelDetail(generic.DetailView):

    template_name = 'generic_views/detail.html'
    model = NonModel

    def get_object(self, queryset=None):
        return NonModel()


class ObjectDoesNotExistDetail(generic.DetailView):
    def get_queryset(self):
        return Book.does_not_exist.all()


class LateValidationView(generic.FormView):
    form_class = ContactForm
    success_url = reverse_lazy('authors_list')
    template_name = 'generic_views/form.html'

    def form_valid(self, form):
        form.add_error(None, 'There is an error')
        return self.form_invalid(form)
