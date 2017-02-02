from django.conf.urls import url
from django.utils.translation import ugettext_lazy as _
from django.views.generic import TemplateView

view = TemplateView.as_view(template_name='dummy.html')

app_name = 'account'
urlpatterns = [
    url(_(r'^register/$'), view, name='register'),
    url(_(r'^register-without-slash$'), view, name='register-without-slash'),
]
