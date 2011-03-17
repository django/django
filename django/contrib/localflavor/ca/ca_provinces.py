""" 
An alphabetical list of provinces and territories for use as `choices` 
in a formfield., and a mapping of province misspellings/abbreviations to 
normalized abbreviations

Source: http://www.canada.gc.ca/othergov/prov_e.html 

This exists in this standalone file so that it's only imported into memory 
when explicitly needed. 
""" 
import warnings
warnings.warn(
    'There have been recent changes to the CA localflavor. See the release notes for details',
    RuntimeWarning
)

PROVINCE_CHOICES = ( 
    ('AB', 'Alberta'), 
    ('BC', 'British Columbia'), 
    ('MB', 'Manitoba'), 
    ('NB', 'New Brunswick'), 
    ('NL', 'Newfoundland and Labrador'),
    ('NT', 'Northwest Territories'), 
    ('NS', 'Nova Scotia'), 
    ('NU', 'Nunavut'), 
    ('ON', 'Ontario'), 
    ('PE', 'Prince Edward Island'), 
    ('QC', 'Quebec'), 
    ('SK', 'Saskatchewan'), 
    ('YT', 'Yukon')
)

PROVINCES_NORMALIZED = {
    'ab': 'AB',
    'alberta': 'AB',
    'bc': 'BC',
    'b.c.': 'BC',
    'british columbia': 'BC',
    'mb': 'MB',
    'manitoba': 'MB',
    'nb': 'NB',
    'new brunswick': 'NB',
    'nf': 'NL',
    'nl': 'NL',
    'newfoundland': 'NL',
    'newfoundland and labrador': 'NL',
    'nt': 'NT',
    'northwest territories': 'NT',
    'ns': 'NS',
    'nova scotia': 'NS',
    'nu': 'NU',
    'nunavut': 'NU',
    'on': 'ON',
    'ontario': 'ON',
    'pe': 'PE',
    'pei': 'PE',
    'p.e.i.': 'PE',
    'prince edward island': 'PE',
    'qc': 'QC',
    'quebec': 'QC',
    'sk': 'SK',
    'saskatchewan': 'SK',
    'yk': 'YT',
    'yt': 'YT',
    'yukon': 'YT',
    'yukon territory': 'YT',
}