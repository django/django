{% block vars %}var geodjango = {};{% for icon in icons %} 
var {{ icon.varname }} = new GIcon(G_DEFAULT_ICON); 
{% if icon.image %}{{ icon.varname }}.image = "{{ icon.image }}";{% endif %}
{% if icon.shadow %}{{ icon.varname }}.shadow = "{{ icon.shadow }}";{% endif %} {% if icon.shadowsize %}{{ icon.varname }}.shadowSize = new GSize({{ icon.shadowsize.0 }}, {{ icon.shadowsize.1 }});{% endif %}
{% if icon.iconanchor %}{{ icon.varname }}.iconAnchor = new GPoint({{ icon.iconanchor.0 }}, {{ icon.iconanchor.1 }});{% endif %} {% if icon.iconsize %}{{ icon.varname }}.iconSize = new GSize({{ icon.iconsize.0 }}, {{ icon.iconsize.1 }});{% endif %}
{% if icon.infowindowanchor %}{{ icon.varname }}.infoWindowAnchor = new GPoint({{ icon.infowindowanchor.0 }}, {{ icon.infowindowanchor.1 }});{% endif %}{% endfor %}{% endblock %}
{% block functions %}{% endblock %}