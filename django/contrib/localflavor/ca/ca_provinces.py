""" 
An alphabetical list of provinces and territories for use as `choices` 
in a formfield., and a mapping of province misspellings/abbreviations to 
normalized abbreviations

Source: http://www.canada.gc.ca/othergov/prov_e.html 

This exists in this standalone file so that it's only imported into memory 
when explicitly needed. 
""" 

PROVINCE_CHOICES = ( 
    ('AB', 'Alberta'), 
    ('BC', 'British Columbia'), 
    ('MB', 'Manitoba'), 
    ('NB', 'New Brunswick'), 
    ('NF', 'Newfoundland and Labrador'), 
    ('NT', 'Northwest Territories'), 
    ('NS', 'Nova Scotia'), 
    ('NU', 'Nunavut'), 
    ('ON', 'Ontario'), 
    ('PE', 'Prince Edward Island'), 
    ('QC', 'Quebec'), 
    ('SK', 'Saskatchewan'), 
    ('YK', 'Yukon') 
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
    'nf': 'NF',
    'newfoundland': 'NF',
    'newfoundland and labrador': 'NF',
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
    'yk': 'YK',
    'yukon': 'YK',
}