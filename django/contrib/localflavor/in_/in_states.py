"""
A mapping of state misspellings/abbreviations to normalized abbreviations, and
an alphabetical list of states for use as `choices` in a formfield.

This exists in this standalone file so that it's only imported into memory
when explicitly needed.
"""

STATE_CHOICES = (
    'KA', 'Karnataka',
    'AP', 'Andhra Pradesh',
    'KL', 'Kerala',
    'TN', 'Tamil Nadu',
    'MH', 'Maharashtra',
    'UP', 'Uttar Pradesh',
    'GA', 'Goa',
    'GJ', 'Gujarat',
    'RJ', 'Rajasthan',
    'HP', 'Himachal Pradesh',
    'JK', 'Jammu and Kashmir',
    'AR', 'Arunachal Pradesh',
    'AS', 'Assam',
    'BR', 'Bihar',
    'CG', 'Chattisgarh',
    'HR', 'Haryana',
    'JH', 'Jharkhand',
    'MP', 'Madhya Pradesh',
    'MN', 'Manipur',
    'ML', 'Meghalaya',
    'MZ', 'Mizoram',
    'NL', 'Nagaland',
    'OR', 'Orissa',
    'PB', 'Punjab',
    'SK', 'Sikkim',
    'TR', 'Tripura',
    'UA', 'Uttarakhand',
    'WB', 'West Bengal',

    # Union Territories
    'AN', 'Andaman and Nicobar',
    'CH', 'Chandigarh',
    'DN', 'Dadra and Nagar Haveli',
    'DD', 'Daman and Diu',
    'DL', 'Delhi',
    'LD', 'Lakshadweep',
    'PY', 'Pondicherry',
)

STATES_NORMALIZED = {
    'ka': 'KA',
    'karnatka': 'KA',
    'tn': 'TN',
    'tamilnad': 'TN',
    'tamilnadu': 'TN',
    'andra pradesh': 'AP',
    'andrapradesh': 'AP',
    'andhrapradesh': 'AP',
    'maharastra': 'MH',
    'mh': 'MH',
    'ap': 'AP',
    'dl': 'DL',
    'dd': 'DD',
    'br': 'BR',
    'ar': 'AR',
    'sk': 'SK',
    'kl': 'KL',
    'ga': 'GA',
    'rj': 'RJ',
    'rajastan': 'RJ',
    'rajasthan': 'RJ',
    'hp': 'HP',
    'ua': 'UA',
    'up': 'UP',
    'mp': 'MP',
    'mz': 'MZ',
    'bengal': 'WB',
    'westbengal': 'WB',
    'mizo': 'MZ',
    'orisa': 'OR',
    'odisa': 'OR',
    'or': 'OR',
    'ar': 'AR',
}

