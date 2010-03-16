from django.forms import ModelForm

from models import Product, Price, Book, DerivedBook, ExplicitPK, Post, DerivedPost

class ProductForm(ModelForm):
    class Meta:
        model = Product

class PriceForm(ModelForm):
    class Meta:
        model = Price

class BookForm(ModelForm):
    class Meta:
       model = Book

class DerivedBookForm(ModelForm):
    class Meta:
        model = DerivedBook

class ExplicitPKForm(ModelForm):
    class Meta:
        model = ExplicitPK
        fields = ('key', 'desc',)

class PostForm(ModelForm):
    class Meta:
        model = Post

class DerivedPostForm(ModelForm):
    class Meta:
        model = DerivedPost
