{% autoescape off %}{% block vars %}var map;{% endblock %}
{% block functions %}{% endblock %}
{% block load %}function {{ load_func }}(){
  if (GBrowserIsCompatible()) {
    map = new GMap2(document.getElementById("{{ dom_id }}"));
    {% block controls %}map.addControl(new GSmallMapControl());
    map.addControl(new GMapTypeControl());{% endblock %}
    map.setCenter(new GLatLng({{ center.1 }}, {{ center.0 }}), {{ zoom }});
    {% for kml_url in kml_urls %}var kml{{ forloop.counter }} = new GGeoXml("{{ kml_url }}");
    map.addOverlay(kml{{ forloop.counter }});{% endfor %}
    {% for polygon in polygons %}var poly{{ forloop.counter }} = new {{ polygon }};
    map.addOverlay(poly{{ forloop.counter }});{% endfor %}
    {% for polyline in polylines %}var polyline{{ forloop.counter }} = new {{ polyline }};
    map.addOverlay(polyline{{ forloop.counter }});{% endfor %}
    {% block load_extra %}{% endblock %}
  }else {
    alert("Sorry, the Google Maps API is not compatible with this browser.");
  }
}
{% endblock %}{% endautoescape %}
