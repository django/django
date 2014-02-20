{% extends "gis/kml/base.kml" %}
{% block placemarks %}{% for place in places %}
  <Placemark>
    <name>{% if place.name %}{{ place.name }}{% else %}{{ place }}{% endif %}</name>
    <description>{% if place.description %}{{ place.description }}{% else %}{{ place }}{% endif %}</description>
    {{ place.kml|safe }}
  </Placemark>{% endfor %}{% endblock %}

