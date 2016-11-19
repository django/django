from django.contrib.auth.models import User
from django.db import models


class MyFileField(models.FileField):
    pass


class Member(models.Model):
    name = models.CharField(max_length=100)
    birthdate = models.DateTimeField(blank=True, null=True)
    gender = models.CharField(max_length=1, blank=True, choices=[('M', 'Male'), ('F', 'Female')])
    email = models.EmailField(blank=True)

    def __str__(self):
        return self.name


class Band(models.Model):
    name = models.CharField(max_length=100)
    style = models.CharField(max_length=20)
    members = models.ManyToManyField(Member)

    def __str__(self):
        return self.name


class Album(models.Model):
    band = models.ForeignKey(Band, models.CASCADE)
    name = models.CharField(max_length=100)
    cover_art = models.FileField(upload_to='albums')
    backside_art = MyFileField(upload_to='albums_back', null=True)

    def __str__(self):
        return self.name


class HiddenInventoryManager(models.Manager):
    def get_queryset(self):
        return super(HiddenInventoryManager, self).get_queryset().filter(hidden=False)


class Inventory(models.Model):
    barcode = models.PositiveIntegerField(unique=True)
    parent = models.ForeignKey('self', models.SET_NULL, to_field='barcode', blank=True, null=True)
    name = models.CharField(blank=False, max_length=20)
    hidden = models.BooleanField(default=False)

    # see #9258
    default_manager = models.Manager()
    objects = HiddenInventoryManager()

    def __str__(self):
        return self.name


class Event(models.Model):
    main_band = models.ForeignKey(
        Band,
        models.CASCADE,
        limit_choices_to=models.Q(pk__gt=0),
        related_name='events_main_band_at',
    )
    supporting_bands = models.ManyToManyField(
        Band,
        blank=True,
        related_name='events_supporting_band_at',
        help_text='Supporting Bands.',
    )
    start_date = models.DateField(blank=True, null=True)
    start_time = models.TimeField(blank=True, null=True)
    description = models.TextField(blank=True)
    link = models.URLField(blank=True)
    min_age = models.IntegerField(blank=True, null=True)


class Car(models.Model):
    owner = models.ForeignKey(User, models.CASCADE)
    make = models.CharField(max_length=30)
    model = models.CharField(max_length=30)

    def __str__(self):
        return "%s %s" % (self.make, self.model)


class CarTire(models.Model):
    """
    A single car tire. This to test that a user can only select their own cars.
    """
    car = models.ForeignKey(Car, models.CASCADE)


class Honeycomb(models.Model):
    location = models.CharField(max_length=20)


class Bee(models.Model):
    """
    A model with a FK to a model that won't be registered with the admin
    (Honeycomb) so the corresponding raw ID widget won't have a magnifying
    glass link to select related honeycomb instances.
    """
    honeycomb = models.ForeignKey(Honeycomb, models.CASCADE)


class Individual(models.Model):
    """
    A model with a FK to itself. It won't be registered with the admin, so the
    corresponding raw ID widget won't have a magnifying glass link to select
    related instances (rendering will be called programmatically in this case).
    """
    name = models.CharField(max_length=20)
    parent = models.ForeignKey('self', models.SET_NULL, null=True)
    soulmate = models.ForeignKey('self', models.CASCADE, null=True, related_name='soulmates')


class Company(models.Model):
    name = models.CharField(max_length=20)


class Advisor(models.Model):
    """
    A model with a m2m to a model that won't be registered with the admin
    (Company) so the corresponding raw ID widget won't have a magnifying
    glass link to select related company instances.
    """
    name = models.CharField(max_length=20)
    companies = models.ManyToManyField(Company)


class Student(models.Model):
    name = models.CharField(max_length=255)

    def __str__(self):
        return self.name

    class Meta:
        ordering = ('name',)


class School(models.Model):
    name = models.CharField(max_length=255)
    students = models.ManyToManyField(Student, related_name='current_schools')
    alumni = models.ManyToManyField(Student, related_name='previous_schools')

    def __str__(self):
        return self.name


class Profile(models.Model):
    user = models.ForeignKey('auth.User', models.CASCADE, to_field='username')

    def __str__(self):
        return self.user.username
