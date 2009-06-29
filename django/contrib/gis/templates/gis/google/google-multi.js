{% extends "gis/google/google-map.js" %}
{% block functions %}
{{ load_map_js }}
{{ js_module }}.load = function(){
    {% for dom_id in dom_ids %}{{ js_module }}.{{ dom_id }}_load();
    {% endfor %}
}
{% endblock %}