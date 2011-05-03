"""
Sources:
    English regions: http://www.statistics.gov.uk/geography/downloads/31_10_01_REGION_names_and_codes_12_00.xls
    Northern Ireland regions: http://en.wikipedia.org/wiki/List_of_Irish_counties_by_area
    Welsh regions: http://en.wikipedia.org/wiki/Preserved_counties_of_Wales
    Scottish regions: http://en.wikipedia.org/wiki/Regions_and_districts_of_Scotland
"""
from django.utils.translation import ugettext_lazy as _

ENGLAND_REGION_CHOICES = (
    ("Bedfordshire", _("Bedfordshire")),
    ("Buckinghamshire", _("Buckinghamshire")),
    ("Cambridgeshire", ("Cambridgeshire")),
    ("Cheshire", _("Cheshire")),
    ("Cornwall and Isles of Scilly", _("Cornwall and Isles of Scilly")),
    ("Cumbria", _("Cumbria")),
    ("Derbyshire", _("Derbyshire")),
    ("Devon", _("Devon")),
    ("Dorset", _("Dorset")),
    ("Durham", _("Durham")),
    ("East Sussex", _("East Sussex")),
    ("Essex", _("Essex")),
    ("Gloucestershire", _("Gloucestershire")),
    ("Greater London", _("Greater London")),
    ("Greater Manchester", _("Greater Manchester")),
    ("Hampshire", _("Hampshire")),
    ("Hertfordshire", _("Hertfordshire")),
    ("Kent", _("Kent")),
    ("Lancashire", _("Lancashire")),
    ("Leicestershire", _("Leicestershire")),
    ("Lincolnshire", _("Lincolnshire")),
    ("Merseyside", _("Merseyside")),
    ("Norfolk", _("Norfolk")),
    ("North Yorkshire", _("North Yorkshire")),
    ("Northamptonshire", _("Northamptonshire")),
    ("Northumberland", _("Northumberland")),
    ("Nottinghamshire", _("Nottinghamshire")),
    ("Oxfordshire", _("Oxfordshire")),
    ("Shropshire", _("Shropshire")),
    ("Somerset", _("Somerset")),
    ("South Yorkshire", _("South Yorkshire")),
    ("Staffordshire", _("Staffordshire")),
    ("Suffolk", _("Suffolk")),
    ("Surrey", _("Surrey")),
    ("Tyne and Wear", _("Tyne and Wear")),
    ("Warwickshire", _("Warwickshire")),
    ("West Midlands", _("West Midlands")),
    ("West Sussex", _("West Sussex")),
    ("West Yorkshire", _("West Yorkshire")),
    ("Wiltshire", _("Wiltshire")),
    ("Worcestershire", _("Worcestershire")),
)

NORTHERN_IRELAND_REGION_CHOICES = (
    ("County Antrim", _("County Antrim")),
    ("County Armagh", _("County Armagh")),
    ("County Down", _("County Down")),
    ("County Fermanagh", _("County Fermanagh")),
    ("County Londonderry", _("County Londonderry")),
    ("County Tyrone", _("County Tyrone")),
)

WALES_REGION_CHOICES = (
    ("Clwyd", _("Clwyd")),
    ("Dyfed", _("Dyfed")),
    ("Gwent", _("Gwent")),
    ("Gwynedd", _("Gwynedd")),
    ("Mid Glamorgan", _("Mid Glamorgan")),
    ("Powys", _("Powys")),
    ("South Glamorgan", _("South Glamorgan")),
    ("West Glamorgan", _("West Glamorgan")),
)

SCOTTISH_REGION_CHOICES = (
    ("Borders", _("Borders")),
    ("Central Scotland", _("Central Scotland")),
    ("Dumfries and Galloway", _("Dumfries and Galloway")),
    ("Fife", _("Fife")),
    ("Grampian", _("Grampian")),
    ("Highland", _("Highland")),
    ("Lothian", _("Lothian")),
    ("Orkney Islands", _("Orkney Islands")),
    ("Shetland Islands", _("Shetland Islands")),
    ("Strathclyde", _("Strathclyde")),
    ("Tayside", _("Tayside")),
    ("Western Isles", _("Western Isles")),
)

GB_NATIONS_CHOICES = (
    ("England", _("England")),
    ("Northern Ireland", _("Northern Ireland")),
    ("Scotland", _("Scotland")),
    ("Wales", _("Wales")),
)

GB_REGION_CHOICES = ENGLAND_REGION_CHOICES + NORTHERN_IRELAND_REGION_CHOICES + WALES_REGION_CHOICES + SCOTTISH_REGION_CHOICES

