# I just raise an AttributeError to confuse the view loading mechanism
raise AttributeError('I am here to confuse django.core.urlresolvers.get_callable')
