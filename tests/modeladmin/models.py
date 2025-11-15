from django.contrib.auth.models import User
from django.db import models


class Band(models.Model):
    name = models.CharField(max_length=100)
    bio = models.TextField()
    sign_date = models.DateField()

    class Meta:
        ordering = ('name',)

    def __str__(self):
        return self.name


class Song(models.Model):
    name = models.CharField(max_length=100)
    band = models.ForeignKey(Band, models.CASCADE)
    featuring = models.ManyToManyField(Band, related_name='featured')

    def __str__(self):
        return self.name


class Concert(models.Model):
    main_band = models.ForeignKey(Band, models.CASCADE, related_name='main_concerts')
    opening_band = models.ForeignKey(Band, models.CASCADE, related_name='opening_concerts', blank=True)
    day = models.CharField(max_length=3, choices=((1, 'Fri'), (2, 'Sat')))
    transport = models.CharField(max_length=100, choices=(
        (1, 'Plane'),
        (2, 'Train'),
        (3, 'Bus')
    ), blank=True)


class ValidationTestModel(models.Model):
    name = models.CharField(max_length=100)
    slug = models.SlugField()
    users = models.ManyToManyField(User)
    state = models.CharField(max_length=2, choices=(("CO", "Colorado"), ("WA", "Washington")))
    is_active = models.BooleanField(default=False)
    pub_date = models.DateTimeField()
    band = models.ForeignKey(Band, models.CASCADE)
    best_friend = models.OneToOneField(User, models.CASCADE, related_name='best_friend')
    # This field is intentionally 2 characters long (#16080).
    no = models.IntegerField(verbose_name="Number", blank=True, null=True)

    def decade_published_in(self):
        return self.pub_date.strftime('%Y')[:3] + "0's"


class ValidationTestInlineModel(models.Model):
    parent = models.ForeignKey(ValidationTestModel, models.CASCADE)


class DescriptorField(models.IntegerField):
    """A custom field that mimics the behavior of django-positions PositionField.

    This field's descriptor raises an exception when accessed on the model class
    (not an instance), which was causing admin.E108 to be incorrectly raised.
    """

    def __init__(self, *args, **kwargs):
        kwargs.setdefault('default', 0)
        super().__init__(*args, **kwargs)

    def contribute_to_class(self, cls, name, **kwargs):
        super().contribute_to_class(cls, name, **kwargs)
        # Replace the descriptor with one that raises when accessed on the class
        setattr(cls, name, DescriptorFieldDescriptor(self))


class DescriptorFieldDescriptor:
    """Descriptor that raises an exception when accessed on the class."""

    def __init__(self, field):
        self.field = field

    def __get__(self, instance, owner):
        if instance is None:
            # Accessing from the class, not an instance - raise an exception
            # This simulates the behavior of django-positions PositionField
            raise AttributeError(
                "DescriptorField can only be accessed via an instance, not the class."
            )
        return instance.__dict__.get(self.field.attname, self.field.default)

    def __set__(self, instance, value):
        instance.__dict__[self.field.attname] = value


class DescriptorModel(models.Model):
    """Test model with a descriptor field that raises on class access."""
    name = models.CharField(max_length=100)
    order = DescriptorField()

    @property
    def a_property(self):
        """A regular property that returns a value."""
        return "property_value"


class ModelWithManyToManyDescriptor(models.Model):
    """Test model to check ManyToMany fields accessed via getattr."""
    name = models.CharField(max_length=100)
    related_items = models.ManyToManyField('self', symmetrical=False)
