from django import http
from django.contrib.databrowse.datastructures import EasyModel
from django.contrib.databrowse.sites import DatabrowsePlugin
from django.shortcuts import render_to_response
import urlparse

class ObjectDetailPlugin(DatabrowsePlugin):
    def model_view(self, request, model_databrowse, url):
        # If the object ID wasn't provided, redirect to the model page, which is one level up.
        if url is None:
            return http.HttpResponseRedirect(urlparse.urljoin(request.path, '../'))
        easy_model = EasyModel(model_databrowse.site, model_databrowse.model)
        obj = easy_model.object_by_pk(url)
        return render_to_response('databrowse/object_detail.html', {'object': obj, 'root_url': model_databrowse.site.root_url})
