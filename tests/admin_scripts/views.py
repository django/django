import os

from django.http import FileResponse


def template_bad_filename(request):

    here = os.path.dirname(__file__)
    f = open(
        os.path.join(here, "custom_templates/project_template.tgz"),
        "rb",
    )

    # a bad filename here, expecting that it joins badly with
    # other paths
    filename = "/bin/archive.tgz"
    response = FileResponse(
        f,
        as_attachment=True,
        filename=filename,
    )

    # Force the filename to have a slash at the beginning
    response["Content-Disposition"] = f'attachment; filename="{filename}"'
    return response
