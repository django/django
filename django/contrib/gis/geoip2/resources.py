def City(response):
    return {
        'city': response.city.name,
        'continent_code': response.continent.code,
        'continent_name': response.continent.name,
        'country_code': response.country.iso_code,
        'country_name': response.country.name,
        'dma_code': response.location.metro_code,
        'is_in_european_union': response.country.is_in_european_union,
        'latitude': response.location.latitude,
        'longitude': response.location.longitude,
        'postal_code': response.postal.code,
        'region': response.subdivisions[0].iso_code if response.subdivisions else None,
        'time_zone': response.location.time_zone,
    }


def Country(response):
    return {
        'country_code': response.country.iso_code,
        'country_name': response.country.name,
    }
