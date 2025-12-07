{% load i18n %}
{% blocktranslate %}Hello{% endblocktranslate %}

This file has a name that should be lexicographically before
'template_with_error.tpl' so that we can test the cleanup case
of the first file being successful, but the second failing.
