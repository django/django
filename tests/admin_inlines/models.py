"""
Testing of admin inline formsets.
"""

import random
import uuid

from django.contrib.contenttypes.fields import GenericForeignKey
from django.contrib.contenttypes.models import ContentType
from django.core.exceptions import ValidationError
from django.db import models


class Parent(models.Model):
    name = models.CharField(max_length=50)

    def __str__(self):
        return self.name


class Teacher(models.Model):
    name = models.CharField(max_length=50)

    def __str__(self):
        return self.name


class Child(models.Model):
    name = models.CharField(max_length=50)
    teacher = models.ForeignKey(Teacher, models.CASCADE)

    content_type = models.ForeignKey(ContentType, models.CASCADE)
    object_id = models.PositiveIntegerField()
    parent = GenericForeignKey()

    def __str__(self):
        return "I am %s, a child of %s" % (self.name, self.parent)


class Book(models.Model):
    name = models.CharField(max_length=50)

    def __str__(self):
        return self.name


class Author(models.Model):
    name = models.CharField(max_length=50)
    books = models.ManyToManyField(Book)
    person = models.OneToOneField("Person", models.CASCADE, null=True)


class NonAutoPKBook(models.Model):
    rand_pk = models.IntegerField(primary_key=True, editable=False)
    author = models.ForeignKey(Author, models.CASCADE)
    title = models.CharField(max_length=50)

    def save(self, *args, **kwargs):
        while not self.rand_pk:
            test_pk = random.randint(1, 99999)
            if not NonAutoPKBook.objects.filter(rand_pk=test_pk).exists():
                self.rand_pk = test_pk
        super().save(*args, **kwargs)


class NonAutoPKBookChild(NonAutoPKBook):
    pass


class EditablePKBook(models.Model):
    manual_pk = models.IntegerField(primary_key=True)
    author = models.ForeignKey(Author, models.CASCADE)
    title = models.CharField(max_length=50)


class Holder(models.Model):
    dummy = models.IntegerField()


class Inner(models.Model):
    dummy = models.IntegerField()
    holder = models.ForeignKey(Holder, models.CASCADE)
    readonly = models.CharField("Inner readonly label", max_length=1)

    def get_absolute_url(self):
        return "/inner/"


class Holder2(models.Model):
    dummy = models.IntegerField()


class Inner2(models.Model):
    dummy = models.IntegerField()
    holder = models.ForeignKey(Holder2, models.CASCADE)


class Holder3(models.Model):
    dummy = models.IntegerField()


class Inner3(models.Model):
    dummy = models.IntegerField()
    holder = models.ForeignKey(Holder3, models.CASCADE)


# Models for ticket #8190


class Holder4(models.Model):
    dummy = models.IntegerField()


class Inner4Stacked(models.Model):
    dummy = models.IntegerField(help_text="Awesome stacked help text is awesome.")
    holder = models.ForeignKey(Holder4, models.CASCADE)

    class Meta:
        constraints = [
            models.UniqueConstraint(
                fields=["dummy", "holder"], name="unique_stacked_dummy_per_holder"
            )
        ]


class Inner4Tabular(models.Model):
    dummy = models.IntegerField(help_text="Awesome tabular help text is awesome.")
    holder = models.ForeignKey(Holder4, models.CASCADE)

    class Meta:
        constraints = [
            models.UniqueConstraint(
                fields=["dummy", "holder"], name="unique_tabular_dummy_per_holder"
            )
        ]


# Models for ticket #31441


class Holder5(models.Model):
    dummy = models.IntegerField()


class Inner5Stacked(models.Model):
    name = models.CharField(max_length=10)
    select = models.CharField(choices=(("1", "One"), ("2", "Two")), max_length=10)
    text = models.TextField()
    dummy = models.IntegerField()
    holder = models.ForeignKey(Holder5, models.CASCADE)


class Inner5Tabular(models.Model):
    name = models.CharField(max_length=10)
    select = models.CharField(choices=(("1", "One"), ("2", "Two")), max_length=10)
    text = models.TextField()
    dummy = models.IntegerField()
    holder = models.ForeignKey(Holder5, models.CASCADE)


# Models for #12749


class Person(models.Model):
    firstname = models.CharField(max_length=15)


class OutfitItem(models.Model):
    name = models.CharField(max_length=15)


class Fashionista(models.Model):
    person = models.OneToOneField(Person, models.CASCADE, primary_key=True)
    weaknesses = models.ManyToManyField(
        OutfitItem, through="ShoppingWeakness", blank=True
    )


class ShoppingWeakness(models.Model):
    fashionista = models.ForeignKey(Fashionista, models.CASCADE)
    item = models.ForeignKey(OutfitItem, models.CASCADE)


# Models for #35189


class Photographer(Person):
    fullname = models.CharField(max_length=100)
    nationality = models.CharField(max_length=100)
    residency = models.CharField(max_length=100)
    siblings = models.IntegerField()
    children = models.IntegerField()


class Photo(models.Model):
    photographer = models.ForeignKey(Photographer, on_delete=models.CASCADE)
    image = models.CharField(max_length=100)
    title = models.CharField(max_length=100)
    description = models.TextField()
    creation_date = models.DateField()
    update_date = models.DateField()
    updated_by = models.CharField(max_length=100)


# Models for #13510


class TitleCollection(models.Model):
    pass


class Title(models.Model):
    collection = models.ForeignKey(
        TitleCollection, models.SET_NULL, blank=True, null=True
    )
    title1 = models.CharField(max_length=100)
    title2 = models.CharField(max_length=100)


# Models for #15424


class Poll(models.Model):
    name = models.CharField(max_length=40)


class Question(models.Model):
    text = models.CharField(max_length=40)
    poll = models.ForeignKey(Poll, models.CASCADE)

    def clean(self):
        raise ValidationError("Always invalid model.")


class Novel(models.Model):
    name = models.CharField(max_length=40)


class NovelReadonlyChapter(Novel):
    class Meta:
        proxy = True


class Chapter(models.Model):
    name = models.CharField(max_length=40)
    novel = models.ForeignKey(Novel, models.CASCADE)


class FootNote(models.Model):
    """
    Model added for ticket 19838
    """

    chapter = models.ForeignKey(Chapter, models.PROTECT)
    note = models.CharField(max_length=40)


# Models for #16838


class CapoFamiglia(models.Model):
    name = models.CharField(max_length=100)


class Consigliere(models.Model):
    name = models.CharField(max_length=100, help_text="Help text for Consigliere")
    capo_famiglia = models.ForeignKey(CapoFamiglia, models.CASCADE, related_name="+")


class SottoCapo(models.Model):
    name = models.CharField(max_length=100)
    capo_famiglia = models.ForeignKey(CapoFamiglia, models.CASCADE, related_name="+")


class ReadOnlyInline(models.Model):
    name = models.CharField(max_length=100, help_text="Help text for ReadOnlyInline")
    capo_famiglia = models.ForeignKey(CapoFamiglia, models.CASCADE)


# Models for #18433


class ParentModelWithCustomPk(models.Model):
    my_own_pk = models.CharField(max_length=100, primary_key=True)
    name = models.CharField(max_length=100)


class ChildModel1(models.Model):
    my_own_pk = models.CharField(max_length=100, primary_key=True)
    name = models.CharField(max_length=100)
    parent = models.ForeignKey(ParentModelWithCustomPk, models.CASCADE)

    def get_absolute_url(self):
        return "/child_model1/"


class ChildModel2(models.Model):
    my_own_pk = models.CharField(max_length=100, primary_key=True)
    name = models.CharField(max_length=100)
    parent = models.ForeignKey(ParentModelWithCustomPk, models.CASCADE)

    def get_absolute_url(self):
        return "/child_model2/"


# Models for #19425
class BinaryTree(models.Model):
    name = models.CharField(max_length=100)
    parent = models.ForeignKey("self", models.SET_NULL, null=True, blank=True)


# Models for #19524


class LifeForm(models.Model):
    pass


class ExtraTerrestrial(LifeForm):
    name = models.CharField(max_length=100)


class Sighting(models.Model):
    et = models.ForeignKey(ExtraTerrestrial, models.CASCADE)
    place = models.CharField(max_length=100)


# Models for #18263
class SomeParentModel(models.Model):
    name = models.CharField(max_length=1)


class SomeChildModel(models.Model):
    name = models.CharField(max_length=1)
    position = models.PositiveIntegerField(help_text="Position help_text.")
    parent = models.ForeignKey(SomeParentModel, models.CASCADE)
    readonly_field = models.CharField(max_length=1)


# Models for #30231
class Course(models.Model):
    name = models.CharField(max_length=128)

    def __str__(self):
        return self.name


class Class(models.Model):
    person = models.ManyToManyField(Person, verbose_name="attendant")
    course = models.ForeignKey(Course, on_delete=models.CASCADE)


class CourseProxy(Course):
    class Meta:
        proxy = True


class CourseProxy1(Course):
    class Meta:
        proxy = True


class CourseProxy2(Course):
    class Meta:
        proxy = True


# Other models
class ShowInlineParent(models.Model):
    show_inlines = models.BooleanField(default=False)


class ShowInlineChild(models.Model):
    parent = models.ForeignKey(ShowInlineParent, on_delete=models.CASCADE)


class ProfileCollection(models.Model):
    pass


class Profile(models.Model):
    collection = models.ForeignKey(
        ProfileCollection, models.SET_NULL, blank=True, null=True
    )
    first_name = models.CharField(max_length=100)
    last_name = models.CharField(max_length=100)


class VerboseNameProfile(Profile):
    class Meta:
        verbose_name = "Model with verbose name only"


class VerboseNamePluralProfile(Profile):
    class Meta:
        verbose_name_plural = "Model with verbose name plural only"


class BothVerboseNameProfile(Profile):
    class Meta:
        verbose_name = "Model with both - name"
        verbose_name_plural = "Model with both - plural name"


class UUIDParent(models.Model):
    pass


class UUIDChild(models.Model):
    id = models.UUIDField(default=uuid.uuid4, primary_key=True)
    title = models.CharField(max_length=128)
    parent = models.ForeignKey(UUIDParent, on_delete=models.CASCADE)
