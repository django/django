from pathlib import Path

from django.http import FileResponse


def template_bad_filename(request):
    content = Path(__file__).parent / "custom_templates" / "project_template.tgz"
    f = open(content, "rb")
    filename = "/nonexistent/archive.tgz"
    response = FileResponse(
        f,
        as_attachment=True,
        filename=filename,
    )
    # Force the filename to have a slash at the beginning.
    response["Content-Disposition"] = f'attachment; filename="{filename}"'
    return response
