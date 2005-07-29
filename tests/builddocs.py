#!/usr/bin/env python
"""
This module builds HTML documentation for models by introspecting the model
unit tests.
"""

from django.core import meta, template
import runtests
import inspect, os, re, sys

MODEL_DOC_TEMPLATE = """
<div class="document" id="model-{{ model_name }}">

<h1 class="title">{{ title }}</h1>
{{ blurb }}

<h2>Model source code</h2>
<pre>{{ model_source }}</pre>

<h2>Sample API usage</h2>
<pre>{{ api_usage }}</pre>
</div>
"""

def make_docs_from_model_tests(output_dir):
    from django.conf import settings

    # Manually set INSTALLED_APPS to point to the test app.
    settings.INSTALLED_APPS = (runtests.APP_NAME,)

    for model_name in runtests.get_test_models():
        mod = meta.get_app(model_name)

        # Clean up the title and blurb.
        title, blurb = mod.__doc__.strip().split('\n', 1)
        blurb = '<p>%s</p>' % blurb.strip().replace('\n\n', '</p><p>')
        api_usage = mod.API_TESTS

        # Get the source code of the model, without the docstring or the
        # API_TESTS variable.
        model_source = inspect.getsource(mod)
        model_source = model_source.replace(mod.__doc__, '')
        model_source = model_source.replace(mod.API_TESTS, '')
        model_source = model_source.replace('""""""\n', '\n')
        model_source = model_source.replace('API_TESTS = ', '')
        model_source = model_source.strip()

        # Run this through the template system.
        t = template.Template(MODEL_DOC_TEMPLATE)
        c = template.Context(locals())
        html = t.render(c)

        file_name = os.path.join(output_dir, 'model_' + model_name + '.html')
        try:
            fp = open(file_name, 'w')
        except IOError:
            sys.stderr.write("Couldn't write to %s.\n" % file_name)
            continue
        else:
            fp.write(html)
            fp.close()

if __name__ == "__main__":
    import sys
    make_docs_from_model_tests(sys.argv[1])
