"""
Tests for the model services for forms.
"""

from django.db import models
from django.newforms.models import form_for_instance, form_for_model
from datetime import date

class Publication(models.Model):
    title = models.CharField(maxlength=30)

    def __str__(self):
        return self.title

    class Meta:
        ordering = ('title',)

class Author(models.Model):
    first_name = models.CharField(maxlength=30)
    last_name = models.CharField(maxlength=30)

    def __str__(self):
        return '%s %s' % (self.first_name, self.last_name)

    class Meta:
        ordering = ('last_name','first_name')
        
class Article(models.Model):
    headline = models.CharField(maxlength=100)
    publication = models.ForeignKey(Publication)
    price = models.FloatField(decimal_places=2, max_digits=8)
    authors = models.ManyToManyField(Author)
    pub_date = models.DateTimeField()

    def __str__(self):
        return self.headline

    class Meta:
        ordering = ('headline',)
        
__test__ = {'API_TESTS':"""
# Create some Authors.
>>> a = Author(first_name='John', last_name='Smith')
>>> a.save()

>>> a2 = Author(first_name='Peter', last_name='Jones')
>>> a2.save()

>>> a3 = Author(first_name='Alice', last_name='Fletcher')
>>> a3.save()

# Create some Publications.
>>> p1 = Publication(id=None, title='The Python Journal')
>>> p1.save()

>>> p2 = Publication(id=None, title='Science News')
>>> p2.save()

# Create an article
>>> art = Article(headline='Django lets you build web apps easily', publication=p1, pub_date=date(2006,02,05), price=2.50)
>>> art.save()

>>> art.authors = [a, a2]

###########################################################
# form_from_model
###########################################################

# Create the Form for the Article model
>>> ArticleForm = form_for_model(Article)

# Instantiate the form with no data
>>> f = ArticleForm()
>>> print f
<tr><th><label for="id_headline">Headline:</label></th><td><input id="id_headline" type="text" name="headline" maxlength="100" /></td></tr>
<tr><th><label for="id_publication">Publication:</label></th><td><select name="publication" id="id_publication">
<option value="" selected="selected">---------</option>
<option value="2">Science News</option>
<option value="1">The Python Journal</option>
</select></td></tr>
<tr><th><label for="id_price">Price:</label></th><td><input type="text" name="price" id="id_price" /></td></tr>
<tr><th><label for="id_pub_date">Pub date:</label></th><td><input type="text" name="pub_date" id="id_pub_date" /></td></tr>
<tr><th><label for="id_authors">Authors:</label></th><td><select multiple="multiple" name="authors" id="id_authors">
<option value="3">Alice Fletcher</option>
<option value="2">Peter Jones</option>
<option value="1">John Smith</option>
</select><br /> Hold down "Control", or "Command" on a Mac, to select more than one.</td></tr>

# Check that the form is not valid
>>> f.is_valid()
False

# Attempt to save the form. Fail, because form cannot be validated
>>> f.save()
Traceback (most recent call last):
...
AttributeError: 'ArticleForm' object has no attribute 'clean_data'

# Instantiate the form with data
>>> f = ArticleForm({'headline':'Django cures cancer!', 'publication': 1, 'price':'3.20', 'pub_date':'2006-11-08', 'authors':[1,2]})
>>> print f
<tr><th><label for="id_headline">Headline:</label></th><td><input id="id_headline" type="text" name="headline" value="Django cures cancer!" maxlength="100" /></td></tr>
<tr><th><label for="id_publication">Publication:</label></th><td><select name="publication" id="id_publication">
<option value="">---------</option>
<option value="2">Science News</option>
<option value="1" selected="selected">The Python Journal</option>
</select></td></tr>
<tr><th><label for="id_price">Price:</label></th><td><input type="text" name="price" value="3.20" id="id_price" /></td></tr>
<tr><th><label for="id_pub_date">Pub date:</label></th><td><input type="text" name="pub_date" value="2006-11-08" id="id_pub_date" /></td></tr>
<tr><th><label for="id_authors">Authors:</label></th><td><select multiple="multiple" name="authors" id="id_authors">
<option value="3">Alice Fletcher</option>
<option value="2" selected="selected">Peter Jones</option>
<option value="1" selected="selected">John Smith</option>
</select><br /> Hold down "Control", or "Command" on a Mac, to select more than one.</td></tr>

# Check that the form is valid
>>> f.is_valid()
True

# Form can be saved!
>>> f.save()
<Article: Django cures cancer!>

# There are now 2 articles
>>> Article.objects.count()
2

# Instantiate the form with data that is missing some fields
>>> f = ArticleForm({'headline':'Django cures cancer!', 'publication': 1, 'authors':[1,2]})
>>> print f
<tr><th><label for="id_headline">Headline:</label></th><td><input id="id_headline" type="text" name="headline" value="Django cures cancer!" maxlength="100" /></td></tr>
<tr><th><label for="id_publication">Publication:</label></th><td><select name="publication" id="id_publication">
<option value="">---------</option>
<option value="2">Science News</option>
<option value="1" selected="selected">The Python Journal</option>
</select></td></tr>
<tr><th><label for="id_price">Price:</label></th><td><ul class="errorlist"><li>This field is required.</li></ul><input type="text" name="price" id="id_price" /></td></tr>
<tr><th><label for="id_pub_date">Pub date:</label></th><td><ul class="errorlist"><li>This field is required.</li></ul><input type="text" name="pub_date" id="id_pub_date" /></td></tr>
<tr><th><label for="id_authors">Authors:</label></th><td><select multiple="multiple" name="authors" id="id_authors">
<option value="3">Alice Fletcher</option>
<option value="2" selected="selected">Peter Jones</option>
<option value="1" selected="selected">John Smith</option>
</select><br /> Hold down "Control", or "Command" on a Mac, to select more than one.</td></tr>

# Check that the form is not valid
>>> f.is_valid()
False

# Attempt to save the form. Fail, because form cannot be validated
>>> f.save()
Traceback (most recent call last):
...
ValueError: The Article could not be created because the data didn't validate.

###########################################################
# form_from_instance 
###########################################################

# Create a Form for an instance of Article
>>> ArticleInstanceForm = form_for_instance(art)

# Instantiate the form with no data
>>> f = ArticleInstanceForm()
>>> print f
<tr><th><label for="id_headline">Headline:</label></th><td><input id="id_headline" type="text" name="headline" value="Django lets you build web apps easily" maxlength="100" /></td></tr>
<tr><th><label for="id_publication">Publication:</label></th><td><select name="publication" id="id_publication">
<option value="">---------</option>
<option value="2">Science News</option>
<option value="1" selected="selected">The Python Journal</option>
</select></td></tr>
<tr><th><label for="id_price">Price:</label></th><td><input type="text" name="price" value="2.5" id="id_price" /></td></tr>
<tr><th><label for="id_pub_date">Pub date:</label></th><td><input type="text" name="pub_date" value="2006-02-05" id="id_pub_date" /></td></tr>
<tr><th><label for="id_authors">Authors:</label></th><td><select multiple="multiple" name="authors" id="id_authors">
<option value="3">Alice Fletcher</option>
<option value="2" selected="selected">Peter Jones</option>
<option value="1" selected="selected">John Smith</option>
</select><br /> Hold down "Control", or "Command" on a Mac, to select more than one.</td></tr>

# Check that the form is not valid (no data dictionary provided)
>>> f.is_valid()
False

# Attempt to save the form. Fail, because form cannot be validated
>>> f.save()
Traceback (most recent call last):
...
AttributeError: 'ArticleInstanceForm' object has no attribute 'clean_data'

# Instantiate the form with data
>>> f = ArticleInstanceForm({'headline':'Nasa uses Python', 'publication': 2, 'price':'4.70', 'pub_date':'2007-01-21', 'authors': [3]})
>>> print f
<tr><th><label for="id_headline">Headline:</label></th><td><input id="id_headline" type="text" name="headline" value="Nasa uses Python" maxlength="100" /></td></tr>
<tr><th><label for="id_publication">Publication:</label></th><td><select name="publication" id="id_publication">
<option value="">---------</option>
<option value="2" selected="selected">Science News</option>
<option value="1">The Python Journal</option>
</select></td></tr>
<tr><th><label for="id_price">Price:</label></th><td><input type="text" name="price" value="4.70" id="id_price" /></td></tr>
<tr><th><label for="id_pub_date">Pub date:</label></th><td><input type="text" name="pub_date" value="2007-01-21" id="id_pub_date" /></td></tr>
<tr><th><label for="id_authors">Authors:</label></th><td><select multiple="multiple" name="authors" id="id_authors">
<option value="3" selected="selected">Alice Fletcher</option>
<option value="2">Peter Jones</option>
<option value="1">John Smith</option>
</select><br /> Hold down "Control", or "Command" on a Mac, to select more than one.</td></tr>

# Check that the form is valid
>>> f.is_valid()
True

# Form can be saved!
>>> f.save()
<Article: Nasa uses Python>

# There are still only 2 articles, as we have saved an existing instance
>>> Article.objects.count()
2


# Instantiate the form with data that is missing some fields
>>> f = ArticleInstanceForm({'headline':'Nasa uses Python', 'publication': 2, 'authors': [3]})
>>> print f
<tr><th><label for="id_headline">Headline:</label></th><td><input id="id_headline" type="text" name="headline" value="Nasa uses Python" maxlength="100" /></td></tr>
<tr><th><label for="id_publication">Publication:</label></th><td><select name="publication" id="id_publication">
<option value="">---------</option>
<option value="2" selected="selected">Science News</option>
<option value="1">The Python Journal</option>
</select></td></tr>
<tr><th><label for="id_price">Price:</label></th><td><ul class="errorlist"><li>This field is required.</li></ul><input type="text" name="price" id="id_price" /></td></tr>
<tr><th><label for="id_pub_date">Pub date:</label></th><td><ul class="errorlist"><li>This field is required.</li></ul><input type="text" name="pub_date" id="id_pub_date" /></td></tr>
<tr><th><label for="id_authors">Authors:</label></th><td><select multiple="multiple" name="authors" id="id_authors">
<option value="3" selected="selected">Alice Fletcher</option>
<option value="2">Peter Jones</option>
<option value="1">John Smith</option>
</select><br /> Hold down "Control", or "Command" on a Mac, to select more than one.</td></tr>

# Check that the form is not valid
>>> f.is_valid()
False

# Attempt to save the form. Fail, because form cannot be validated
>>> f.save()
Traceback (most recent call last):
...
ValueError: The Article could not be changed because the data didn't validate.

"""}
