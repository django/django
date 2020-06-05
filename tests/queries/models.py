"""
Various complex queries that have been problematic in the past.
"""
import threading

from django.db import models
from django.db.models.functions import Now


class DumbCategory(models.Model):
    pass


class ProxyCategory(DumbCategory):
    class Meta:
        proxy = True


class NamedCategory(DumbCategory):
    name = models.CharField(max_length=10)

    def __str__(self):
        return self.name


class Tag(models.Model):
    name = models.CharField(max_length=10)
    parent = models.ForeignKey(
        'self',
        models.SET_NULL,
        blank=True, null=True,
        related_name='children',
    )
    category = models.ForeignKey(NamedCategory, models.SET_NULL, null=True, default=None)

    class Meta:
        ordering = ['name']

    def __str__(self):
        return self.name


class Note(models.Model):
    note = models.CharField(max_length=100)
    misc = models.CharField(max_length=10)
    tag = models.ForeignKey(Tag, models.SET_NULL, blank=True, null=True)

    class Meta:
        ordering = ['note']

    def __str__(self):
        return self.note

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        # Regression for #13227 -- having an attribute that
        # is unpicklable doesn't stop you from cloning queries
        # that use objects of that type as an argument.
        self.lock = threading.Lock()


class Annotation(models.Model):
    name = models.CharField(max_length=10)
    tag = models.ForeignKey(Tag, models.CASCADE)
    notes = models.ManyToManyField(Note)

    def __str__(self):
        return self.name


class DateTimePK(models.Model):
    date = models.DateTimeField(primary_key=True, auto_now_add=True)


class ExtraInfo(models.Model):
    info = models.CharField(max_length=100)
    note = models.ForeignKey(Note, models.CASCADE, null=True)
    value = models.IntegerField(null=True)
    date = models.ForeignKey(DateTimePK, models.SET_NULL, null=True)
    filterable = models.BooleanField(default=True)

    class Meta:
        ordering = ['info']

    def __str__(self):
        return self.info


class Author(models.Model):
    name = models.CharField(max_length=10)
    num = models.IntegerField(unique=True)
    extra = models.ForeignKey(ExtraInfo, models.CASCADE)

    class Meta:
        ordering = ['name']

    def __str__(self):
        return self.name


class Item(models.Model):
    name = models.CharField(max_length=10)
    created = models.DateTimeField()
    modified = models.DateTimeField(blank=True, null=True)
    tags = models.ManyToManyField(Tag, blank=True)
    creator = models.ForeignKey(Author, models.CASCADE)
    note = models.ForeignKey(Note, models.CASCADE)

    class Meta:
        ordering = ['-note', 'name']

    def __str__(self):
        return self.name


class Report(models.Model):
    name = models.CharField(max_length=10)
    creator = models.ForeignKey(Author, models.SET_NULL, to_field='num', null=True)

    def __str__(self):
        return self.name


class ReportComment(models.Model):
    report = models.ForeignKey(Report, models.CASCADE)


class Ranking(models.Model):
    rank = models.IntegerField()
    author = models.ForeignKey(Author, models.CASCADE)

    class Meta:
        # A complex ordering specification. Should stress the system a bit.
        ordering = ('author__extra__note', 'author__name', 'rank')

    def __str__(self):
        return '%d: %s' % (self.rank, self.author.name)


class Cover(models.Model):
    title = models.CharField(max_length=50)
    item = models.ForeignKey(Item, models.CASCADE)

    class Meta:
        ordering = ['item']

    def __str__(self):
        return self.title


class Number(models.Model):
    num = models.IntegerField()
    other_num = models.IntegerField(null=True)

    def __str__(self):
        return str(self.num)

# Symmetrical m2m field with a normal field using the reverse accessor name
# ("valid").


class Valid(models.Model):
    valid = models.CharField(max_length=10)
    parent = models.ManyToManyField('self')

    class Meta:
        ordering = ['valid']

# Some funky cross-linked models for testing a couple of infinite recursion
# cases.


class X(models.Model):
    y = models.ForeignKey('Y', models.CASCADE)


class Y(models.Model):
    x1 = models.ForeignKey(X, models.CASCADE, related_name='y1')

# Some models with a cycle in the default ordering. This would be bad if we
# didn't catch the infinite loop.


class LoopX(models.Model):
    y = models.ForeignKey('LoopY', models.CASCADE)

    class Meta:
        ordering = ['y']


class LoopY(models.Model):
    x = models.ForeignKey(LoopX, models.CASCADE)

    class Meta:
        ordering = ['x']


class LoopZ(models.Model):
    z = models.ForeignKey('self', models.CASCADE)

    class Meta:
        ordering = ['z']


# A model and custom default manager combination.


class CustomManager(models.Manager):
    def get_queryset(self):
        qs = super().get_queryset()
        return qs.filter(public=True, tag__name='t1')


class ManagedModel(models.Model):
    data = models.CharField(max_length=10)
    tag = models.ForeignKey(Tag, models.CASCADE)
    public = models.BooleanField(default=True)

    objects = CustomManager()
    normal_manager = models.Manager()

    def __str__(self):
        return self.data

# An inter-related setup with multiple paths from Child to Detail.


class Detail(models.Model):
    data = models.CharField(max_length=10)


class MemberManager(models.Manager):
    def get_queryset(self):
        return super().get_queryset().select_related("details")


class Member(models.Model):
    name = models.CharField(max_length=10)
    details = models.OneToOneField(Detail, models.CASCADE, primary_key=True)

    objects = MemberManager()


class Child(models.Model):
    person = models.OneToOneField(Member, models.CASCADE, primary_key=True)
    parent = models.ForeignKey(Member, models.CASCADE, related_name="children")

# Custom primary keys interfered with ordering in the past.


class CustomPk(models.Model):
    name = models.CharField(max_length=10, primary_key=True)
    extra = models.CharField(max_length=10)

    class Meta:
        ordering = ['name', 'extra']


class Related(models.Model):
    custom = models.ForeignKey(CustomPk, models.CASCADE, null=True)


class CustomPkTag(models.Model):
    id = models.CharField(max_length=20, primary_key=True)
    custom_pk = models.ManyToManyField(CustomPk)
    tag = models.CharField(max_length=20)

# An inter-related setup with a model subclass that has a nullable
# path to another model, and a return path from that model.


class Celebrity(models.Model):
    name = models.CharField("Name", max_length=20)
    greatest_fan = models.ForeignKey("Fan", models.SET_NULL, null=True, unique=True)

    def __str__(self):
        return self.name


class TvChef(Celebrity):
    pass


class Fan(models.Model):
    fan_of = models.ForeignKey(Celebrity, models.CASCADE)

# Multiple foreign keys


class LeafA(models.Model):
    data = models.CharField(max_length=10)

    def __str__(self):
        return self.data


class LeafB(models.Model):
    data = models.CharField(max_length=10)


class Join(models.Model):
    a = models.ForeignKey(LeafA, models.CASCADE)
    b = models.ForeignKey(LeafB, models.CASCADE)


class ReservedName(models.Model):
    name = models.CharField(max_length=20)
    order = models.IntegerField()

    def __str__(self):
        return self.name

# A simpler shared-foreign-key setup that can expose some problems.


class SharedConnection(models.Model):
    data = models.CharField(max_length=10)

    def __str__(self):
        return self.data


class PointerA(models.Model):
    connection = models.ForeignKey(SharedConnection, models.CASCADE)


class PointerB(models.Model):
    connection = models.ForeignKey(SharedConnection, models.CASCADE)

# Multi-layer ordering


class SingleObject(models.Model):
    name = models.CharField(max_length=10)

    class Meta:
        ordering = ['name']

    def __str__(self):
        return self.name


class RelatedObject(models.Model):
    single = models.ForeignKey(SingleObject, models.SET_NULL, null=True)
    f = models.IntegerField(null=True)

    class Meta:
        ordering = ['single']


class Plaything(models.Model):
    name = models.CharField(max_length=10)
    others = models.ForeignKey(RelatedObject, models.SET_NULL, null=True)

    class Meta:
        ordering = ['others']

    def __str__(self):
        return self.name


class Article(models.Model):
    name = models.CharField(max_length=20)
    created = models.DateTimeField()

    def __str__(self):
        return self.name


class Food(models.Model):
    name = models.CharField(max_length=20, unique=True)

    def __str__(self):
        return self.name


class Eaten(models.Model):
    food = models.ForeignKey(Food, models.SET_NULL, to_field="name", null=True)
    meal = models.CharField(max_length=20)

    def __str__(self):
        return "%s at %s" % (self.food, self.meal)


class Node(models.Model):
    num = models.IntegerField(unique=True)
    parent = models.ForeignKey("self", models.SET_NULL, to_field="num", null=True)

    def __str__(self):
        return "%s" % self.num

# Bug #12252


class ObjectA(models.Model):
    name = models.CharField(max_length=50)

    def __str__(self):
        return self.name

    def __iter__(self):
        # Ticket #23721
        assert False, 'type checking should happen without calling model __iter__'


class ProxyObjectA(ObjectA):
    class Meta:
        proxy = True


class ChildObjectA(ObjectA):
    pass


class ObjectB(models.Model):
    name = models.CharField(max_length=50)
    objecta = models.ForeignKey(ObjectA, models.CASCADE)
    num = models.PositiveSmallIntegerField()

    def __str__(self):
        return self.name


class ProxyObjectB(ObjectB):
    class Meta:
        proxy = True


class ObjectC(models.Model):
    name = models.CharField(max_length=50)
    objecta = models.ForeignKey(ObjectA, models.SET_NULL, null=True)
    objectb = models.ForeignKey(ObjectB, models.SET_NULL, null=True)
    childobjecta = models.ForeignKey(ChildObjectA, models.SET_NULL, null=True, related_name='ca_pk')

    def __str__(self):
        return self.name


class SimpleCategory(models.Model):
    name = models.CharField(max_length=15)

    def __str__(self):
        return self.name


class SpecialCategory(SimpleCategory):
    special_name = models.CharField(max_length=15)

    def __str__(self):
        return self.name + " " + self.special_name


class CategoryItem(models.Model):
    category = models.ForeignKey(SimpleCategory, models.CASCADE)

    def __str__(self):
        return "category item: " + str(self.category)


class MixedCaseFieldCategoryItem(models.Model):
    CaTeGoRy = models.ForeignKey(SimpleCategory, models.CASCADE)


class MixedCaseDbColumnCategoryItem(models.Model):
    category = models.ForeignKey(SimpleCategory, models.CASCADE, db_column='CaTeGoRy_Id')


class OneToOneCategory(models.Model):
    new_name = models.CharField(max_length=15)
    category = models.OneToOneField(SimpleCategory, models.CASCADE)

    def __str__(self):
        return "one2one " + self.new_name


class CategoryRelationship(models.Model):
    first = models.ForeignKey(SimpleCategory, models.CASCADE, related_name='first_rel')
    second = models.ForeignKey(SimpleCategory, models.CASCADE, related_name='second_rel')


class CommonMixedCaseForeignKeys(models.Model):
    category = models.ForeignKey(CategoryItem, models.CASCADE)
    mixed_case_field_category = models.ForeignKey(MixedCaseFieldCategoryItem, models.CASCADE)
    mixed_case_db_column_category = models.ForeignKey(MixedCaseDbColumnCategoryItem, models.CASCADE)


class NullableName(models.Model):
    name = models.CharField(max_length=20, null=True)

    class Meta:
        ordering = ['id']


class ModelD(models.Model):
    name = models.TextField()


class ModelC(models.Model):
    name = models.TextField()


class ModelB(models.Model):
    name = models.TextField()
    c = models.ForeignKey(ModelC, models.CASCADE)


class ModelA(models.Model):
    name = models.TextField()
    b = models.ForeignKey(ModelB, models.SET_NULL, null=True)
    d = models.ForeignKey(ModelD, models.CASCADE)


class Job(models.Model):
    name = models.CharField(max_length=20, unique=True)

    def __str__(self):
        return self.name


class JobResponsibilities(models.Model):
    job = models.ForeignKey(Job, models.CASCADE, to_field='name')
    responsibility = models.ForeignKey('Responsibility', models.CASCADE, to_field='description')


class Responsibility(models.Model):
    description = models.CharField(max_length=20, unique=True)
    jobs = models.ManyToManyField(Job, through=JobResponsibilities,
                                  related_name='responsibilities')

    def __str__(self):
        return self.description

# Models for disjunction join promotion low level testing.


class FK1(models.Model):
    f1 = models.TextField()
    f2 = models.TextField()


class FK2(models.Model):
    f1 = models.TextField()
    f2 = models.TextField()


class FK3(models.Model):
    f1 = models.TextField()
    f2 = models.TextField()


class BaseA(models.Model):
    a = models.ForeignKey(FK1, models.SET_NULL, null=True)
    b = models.ForeignKey(FK2, models.SET_NULL, null=True)
    c = models.ForeignKey(FK3, models.SET_NULL, null=True)


class Identifier(models.Model):
    name = models.CharField(max_length=100)

    def __str__(self):
        return self.name


class Program(models.Model):
    identifier = models.OneToOneField(Identifier, models.CASCADE)


class Channel(models.Model):
    programs = models.ManyToManyField(Program)
    identifier = models.OneToOneField(Identifier, models.CASCADE)


class Book(models.Model):
    title = models.TextField()
    chapter = models.ForeignKey('Chapter', models.CASCADE)


class Chapter(models.Model):
    title = models.TextField()
    paragraph = models.ForeignKey('Paragraph', models.CASCADE)


class Paragraph(models.Model):
    text = models.TextField()
    page = models.ManyToManyField('Page')


class Page(models.Model):
    text = models.TextField()


class MyObject(models.Model):
    parent = models.ForeignKey('self', models.SET_NULL, null=True, blank=True, related_name='children')
    data = models.CharField(max_length=100)
    created_at = models.DateTimeField(auto_now_add=True)

# Models for #17600 regressions


class Order(models.Model):
    id = models.IntegerField(primary_key=True)
    name = models.CharField(max_length=12, null=True, default='')

    class Meta:
        ordering = ('pk',)

    def __str__(self):
        return '%s' % self.pk


class OrderItem(models.Model):
    order = models.ForeignKey(Order, models.CASCADE, related_name='items')
    status = models.IntegerField()

    class Meta:
        ordering = ('pk',)

    def __str__(self):
        return '%s' % self.pk


class BaseUser(models.Model):
    pass


class Task(models.Model):
    title = models.CharField(max_length=10)
    owner = models.ForeignKey(BaseUser, models.CASCADE, related_name='owner')
    creator = models.ForeignKey(BaseUser, models.CASCADE, related_name='creator')

    def __str__(self):
        return self.title


class Staff(models.Model):
    name = models.CharField(max_length=10)

    def __str__(self):
        return self.name


class StaffUser(BaseUser):
    staff = models.OneToOneField(Staff, models.CASCADE, related_name='user')

    def __str__(self):
        return self.staff


class Ticket21203Parent(models.Model):
    parentid = models.AutoField(primary_key=True)
    parent_bool = models.BooleanField(default=True)
    created = models.DateTimeField(auto_now=True)


class Ticket21203Child(models.Model):
    childid = models.AutoField(primary_key=True)
    parent = models.ForeignKey(Ticket21203Parent, models.CASCADE)


class Person(models.Model):
    name = models.CharField(max_length=128)


class Company(models.Model):
    name = models.CharField(max_length=128)
    employees = models.ManyToManyField(Person, related_name='employers', through='Employment')

    def __str__(self):
        return self.name


class Employment(models.Model):
    employer = models.ForeignKey(Company, models.CASCADE)
    employee = models.ForeignKey(Person, models.CASCADE)
    title = models.CharField(max_length=128)


class School(models.Model):
    pass


class Student(models.Model):
    school = models.ForeignKey(School, models.CASCADE)


class Classroom(models.Model):
    name = models.CharField(max_length=20)
    has_blackboard = models.BooleanField(null=True)
    school = models.ForeignKey(School, models.CASCADE)
    students = models.ManyToManyField(Student, related_name='classroom')


class Teacher(models.Model):
    schools = models.ManyToManyField(School)
    friends = models.ManyToManyField('self')


class Ticket23605AParent(models.Model):
    pass


class Ticket23605A(Ticket23605AParent):
    pass


class Ticket23605B(models.Model):
    modela_fk = models.ForeignKey(Ticket23605A, models.CASCADE)
    modelc_fk = models.ForeignKey("Ticket23605C", models.CASCADE)
    field_b0 = models.IntegerField(null=True)
    field_b1 = models.BooleanField(default=False)


class Ticket23605C(models.Model):
    field_c0 = models.FloatField()


# db_table names have capital letters to ensure they are quoted in queries.
class Individual(models.Model):
    alive = models.BooleanField()

    class Meta:
        db_table = 'Individual'


class RelatedIndividual(models.Model):
    related = models.ForeignKey(Individual, models.CASCADE, related_name='related_individual')

    class Meta:
        db_table = 'RelatedIndividual'


class CustomDbColumn(models.Model):
    custom_column = models.IntegerField(db_column='custom_name', null=True)
    ip_address = models.GenericIPAddressField(null=True)


class CreatedField(models.DateTimeField):
    db_returning = True

    def __init__(self, *args, **kwargs):
        kwargs.setdefault('default', Now)
        super().__init__(*args, **kwargs)


class ReturningModel(models.Model):
    created = CreatedField(editable=False)


class NonIntegerPKReturningModel(models.Model):
    created = CreatedField(editable=False, primary_key=True)
