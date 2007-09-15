from django.db import models

class BoundaryModel(models.Model): 
    positive_integer = models.PositiveIntegerField(null=True, blank=True)
    
__test__ = {'API_TESTS': """
>>> from django.newforms import form_for_model

# Boundary conditions on a PostitiveIntegerField #########################
>>> BoundaryForm = form_for_model(BoundaryModel) 
>>> f = BoundaryForm({'positive_integer':100}) 
>>> f.is_valid() 
True
>>> f = BoundaryForm({'positive_integer':0}) 
>>> f.is_valid() 
True
>>> f = BoundaryForm({'positive_integer':-100}) 
>>> f.is_valid() 
False

"""}