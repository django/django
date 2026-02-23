import os

from django.http import HttpResponse


def template_bad_filename(request):

    here = os.path.dirname(__file__)
    with open(os.path.join(here, "custom_templates/project_template.tgz"), "rb") as f:
        file_data = f.read()

    # a bad filename here, expecting that it joins badly with
    # other paths
    filename = "/bin/archive.tgz"
    response = HttpResponse(file_data, content_type="application/octet-stream")
    response["Content-Disposition"] = f'attachment; filename="{filename}"'
    return response
