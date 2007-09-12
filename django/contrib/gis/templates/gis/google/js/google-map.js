{% block vars %}var map;{% for kml_url in kml_urls %}var kml{{ forloop.counter }};{% endfor %}{% endblock %}
{% block functions %}{% endblock %}
{% block load %}function {{ load_func }}(){
  if (GBrowserIsCompatible()) {
    map = new GMap2(document.getElementById("{{ dom_id }}"));
    map.addControl(new GSmallMapControl());
    map.addControl(new GMapTypeControl());
    map.setCenter(new GLatLng({{ center_lat }}, {{ center_lon }}), {{ zoom }});
    {% for kml_url in kml_urls %}kml{{ forloop.counter }} = new GGeoXml("{{ kml_url }}");
    map.addOverlay(kml{{ forloop.counter }});{% endfor %}
    {% block load_extra %}{% endblock %}
  }else {
    alert("Sorry, the Google Maps API is not compatible with this browser.");
  }
}
{% endblock %}