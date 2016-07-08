def City(response):
    return {
        'city': response.city.name,
        'country_code': response.country.iso_code,
        'country_name': response.country.name,
        'dma_code': response.location.metro_code,
        'latitude': response.location.latitude,
        'longitude': response.location.longitude,
        'postal_code': response.postal.code,
        'region': response.subdivisions[0].iso_code if len(response.subdivisions) else None,
    }


def Country(response):
    return {
        'country_code': response.country.iso_code,
        'country_name': response.country.name,
    }
