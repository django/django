{% extends "gis/admin/openlayers.js" %}
{% block base_layer %}new OpenLayers.Layer.OSM.Mapnik("OpenStreetMap (Mapnik)");{% endblock %}
