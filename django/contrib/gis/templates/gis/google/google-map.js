{% load l10n %}
{% autoescape off %}
{% localize off %}
{% block vars %}var geodjango = {};{% for icon in icons %}
var {{ icon.varname }} = new GIcon(G_DEFAULT_ICON);
{% if icon.image %}{{ icon.varname }}.image = "{{ icon.image }}";{% endif %}
{% if icon.shadow %}{{ icon.varname }}.shadow = "{{ icon.shadow }}";{% endif %} {% if icon.shadowsize %}{{ icon.varname }}.shadowSize = new GSize({{ icon.shadowsize.0 }}, {{ icon.shadowsize.1 }});{% endif %}
{% if icon.iconanchor %}{{ icon.varname }}.iconAnchor = new GPoint({{ icon.iconanchor.0 }}, {{ icon.iconanchor.1 }});{% endif %} {% if icon.iconsize %}{{ icon.varname }}.iconSize = new GSize({{ icon.iconsize.0 }}, {{ icon.iconsize.1 }});{% endif %}
{% if icon.infowindowanchor %}{{ icon.varname }}.infoWindowAnchor = new GPoint({{ icon.infowindowanchor.0 }}, {{ icon.infowindowanchor.1 }});{% endif %}{% endfor %}
{% endblock vars %}{% block functions %}
{% block load %}{{ js_module }}.{{ dom_id }}_load = function(){
  if (GBrowserIsCompatible()) {
    {{ js_module }}.{{ dom_id }} = new GMap2(document.getElementById("{{ dom_id }}"));
    {{ js_module }}.{{ dom_id }}.setCenter(new GLatLng({{ center.1 }}, {{ center.0 }}), {{ zoom }});
    {% block controls %}{{ js_module }}.{{ dom_id }}.setUIToDefault();{% endblock %}
    {% if calc_zoom %}var bounds = new GLatLngBounds(); var tmp_bounds = new GLatLngBounds();{% endif %}
    {% for kml_url in kml_urls %}{{ js_module }}.{{ dom_id }}_kml{{ forloop.counter }} = new GGeoXml("{{ kml_url }}");
    {{ js_module }}.{{ dom_id }}.addOverlay({{ js_module }}.{{ dom_id }}_kml{{ forloop.counter }});{% endfor %}
    {% for polygon in polygons %}{{ js_module }}.{{ dom_id }}_poly{{ forloop.counter }} = new {{ polygon }};
    {{ js_module }}.{{ dom_id }}.addOverlay({{ js_module }}.{{ dom_id }}_poly{{ forloop.counter }});
    {% for event in polygon.events %}GEvent.addListener({{ js_module }}.{{ dom_id }}_poly{{ forloop.parentloop.counter }}, {{ event }});{% endfor %}
    {% if calc_zoom %}tmp_bounds = {{ js_module }}.{{ dom_id }}_poly{{ forloop.counter }}.getBounds(); bounds.extend(tmp_bounds.getSouthWest()); bounds.extend(tmp_bounds.getNorthEast());{% endif %}{% endfor %}
    {% for polyline in polylines %}{{ js_module }}.{{ dom_id }}_polyline{{ forloop.counter }} = new {{ polyline }};
    {{ js_module }}.{{ dom_id }}.addOverlay({{ js_module }}.{{ dom_id }}_polyline{{ forloop.counter }});
    {% for event in polyline.events %}GEvent.addListener({{ js_module }}.{{ dom_id }}_polyline{{ forloop.parentloop.counter }}, {{ event }}); {% endfor %}
    {% if calc_zoom %}tmp_bounds = {{ js_module }}.{{ dom_id }}_polyline{{ forloop.counter }}.getBounds(); bounds.extend(tmp_bounds.getSouthWest()); bounds.extend(tmp_bounds.getNorthEast());{% endif %}{% endfor %}
    {% for marker in markers %}{{ js_module }}.{{ dom_id }}_marker{{ forloop.counter }} = new {{ marker }};
    {{ js_module }}.{{ dom_id }}.addOverlay({{ js_module }}.{{ dom_id }}_marker{{ forloop.counter }});
    {% for event in marker.events %}GEvent.addListener({{ js_module }}.{{ dom_id }}_marker{{ forloop.parentloop.counter }}, {{ event }}); {% endfor %}
    {% if calc_zoom %}bounds.extend({{ js_module }}.{{ dom_id }}_marker{{ forloop.counter }}.getLatLng()); {% endif %}{% endfor %}
    {% if calc_zoom %}{{ js_module }}.{{ dom_id }}.setCenter(bounds.getCenter(), {{ js_module }}.{{ dom_id }}.getBoundsZoomLevel(bounds));{% endif %}
    {% block load_extra %}{% endblock %}
  }else {
    alert("Sorry, the Google Maps API is not compatible with this browser.");
  }
}
{% endblock load %}{% endblock functions %}{% endlocalize %}{% endautoescape %}
