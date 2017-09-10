#!/usr/bin/env python
# -*- coding: utf-8 -*-


# ==============================================================================
#
#       File Name : unprefixed_urls.py
#
#       Purpose :
#
#       Creation Date : Sun 10 Sep 2017 10:35:45 PM EEST
#
#       Last Modified : Sun 10 Sep 2017 11:30:47 PM EEST
#
#       Developer : rara_tiru  | email: tantiras@yandex.com
#
# ==============================================================================

from django.conf.urls import url
from django.conf.urls import include
from django.conf.urls.i18n import i18n_patterns
from django.utils.translation import gettext_lazy as _
from django.http import HttpResponse
from django.contrib import admin

urlpatterns = [
    url(r'^i18n/', include('django.conf.urls.i18n')),
]

urlpatterns += i18n_patterns(
    url(r'^admin/', admin.site.urls),
    prefix_default_language=False,
)
