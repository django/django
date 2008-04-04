{% autoescape off %}{% block vars %}var map;{% endblock %}
{% block functions %}{% endblock %}
{% block load %}function {{ load_func }}(){
  if (GBrowserIsCompatible()) {
    map = new GMap2(document.getElementById("{{ dom_id }}"));
    {% block controls %}map.addControl(new GSmallMapControl());
    map.addControl(new GMapTypeControl());{% endblock %}
    {% if calc_zoom %}var bounds = new GLatLngBounds(); var tmp_bounds = new GLatLngBounds();{% else %}map.setCenter(new GLatLng({{ center.1 }}, {{ center.0 }}), {{ zoom }});{% endif %}
    {% for kml_url in kml_urls %}var kml{{ forloop.counter }} = new GGeoXml("{{ kml_url }}");
    map.addOverlay(kml{{ forloop.counter }});{% endfor %}
    {% for polygon in polygons %}var poly{{ forloop.counter }} = new {{ polygon }};
    map.addOverlay(poly{{ forloop.counter }});{% if calc_zoom %}
    tmp_bounds = poly{{ forloop.counter }}.getBounds(); bounds.extend(tmp_bounds.getSouthWest()); bounds.extend(tmp_bounds.getNorthEast());{% endif %}{% endfor %}
    {% for polyline in polylines %}var polyline{{ forloop.counter }} = new {{ polyline }};
    map.addOverlay(polyline{{ forloop.counter }});{% if calc_zoom %}
    tmp_bounds = polyline{{ forloop.counter }}.getBounds(); bounds.extend(tmp_bounds.getSouthWest()); bounds.extend(tmp_bounds.getNorthEast());{% endif %}{% endfor %}
    {% if calc_zoom %}map.setCenter(bounds.getCenter(), map.getBoundsZoomLevel(bounds));{% endif %}
    {% block load_extra %}{% endblock %}
  }else {
    alert("Sorry, the Google Maps API is not compatible with this browser.");
  }
}
{% endblock %}{% endautoescape %}
