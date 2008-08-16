# -*- coding: utf-8 -*-
# Tests for the contrib/localflavor/ ES form fields.

tests = r"""
# ESPostalCodeField ##############################################################

ESPostalCodeField validates that data is a five-digit spanish postal code.
>>> from django.contrib.localflavor.es.forms import ESPostalCodeField
>>> f = ESPostalCodeField()
>>> f.clean('08028')
u'08028'
>>> f.clean('28080')
u'28080'
>>> f.clean('53001')
Traceback (most recent call last):
...
ValidationError: [u'Enter a valid postal code in the range and format 01XXX - 52XXX.']
>>> f.clean('0801')
Traceback (most recent call last):
...
ValidationError: [u'Enter a valid postal code in the range and format 01XXX - 52XXX.']
>>> f.clean('080001')
Traceback (most recent call last):
...
ValidationError: [u'Enter a valid postal code in the range and format 01XXX - 52XXX.']
>>> f.clean('00999')
Traceback (most recent call last):
...
ValidationError: [u'Enter a valid postal code in the range and format 01XXX - 52XXX.']
>>> f.clean('08 01')
Traceback (most recent call last):
...
ValidationError: [u'Enter a valid postal code in the range and format 01XXX - 52XXX.']
>>> f.clean('08A01')
Traceback (most recent call last):
...
ValidationError: [u'Enter a valid postal code in the range and format 01XXX - 52XXX.']
>>> f.clean('')
Traceback (most recent call last):
...
ValidationError: [u'This field is required.']

>>> f = ESPostalCodeField(required=False)
>>> f.clean('08028')
u'08028'
>>> f.clean('28080')
u'28080'
>>> f.clean('53001')
Traceback (most recent call last):
...
ValidationError: [u'Enter a valid postal code in the range and format 01XXX - 52XXX.']
>>> f.clean('0801')
Traceback (most recent call last):
...
ValidationError: [u'Enter a valid postal code in the range and format 01XXX - 52XXX.']
>>> f.clean('080001')
Traceback (most recent call last):
...
ValidationError: [u'Enter a valid postal code in the range and format 01XXX - 52XXX.']
>>> f.clean('00999')
Traceback (most recent call last):
...
ValidationError: [u'Enter a valid postal code in the range and format 01XXX - 52XXX.']
>>> f.clean('08 01')
Traceback (most recent call last):
...
ValidationError: [u'Enter a valid postal code in the range and format 01XXX - 52XXX.']
>>> f.clean('08A01')
Traceback (most recent call last):
...
ValidationError: [u'Enter a valid postal code in the range and format 01XXX - 52XXX.']
>>> f.clean('')
u''

# ESPhoneNumberField ##############################################################

ESPhoneNumberField validates that data is a nine-digit spanish phone number.
>>> from django.contrib.localflavor.es.forms import ESPhoneNumberField
>>> f = ESPhoneNumberField()
>>> f.clean('650010101')
u'650010101'
>>> f.clean('931234567')
u'931234567'
>>> f.clean('800123123')
u'800123123'
>>> f.clean('555555555')
Traceback (most recent call last):
...
ValidationError: [u'Enter a valid phone number in one of the formats 6XXXXXXXX, 8XXXXXXXX or 9XXXXXXXX.']
>>> f.clean('789789789')
Traceback (most recent call last):
...
ValidationError: [u'Enter a valid phone number in one of the formats 6XXXXXXXX, 8XXXXXXXX or 9XXXXXXXX.']
>>> f.clean('99123123')
Traceback (most recent call last):
...
ValidationError: [u'Enter a valid phone number in one of the formats 6XXXXXXXX, 8XXXXXXXX or 9XXXXXXXX.']
>>> f.clean('9999123123')
Traceback (most recent call last):
...
ValidationError: [u'Enter a valid phone number in one of the formats 6XXXXXXXX, 8XXXXXXXX or 9XXXXXXXX.']
>>> f.clean('')
Traceback (most recent call last):
...
ValidationError: [u'This field is required.']

>>> f = ESPhoneNumberField(required=False)
>>> f.clean('650010101')
u'650010101'
>>> f.clean('931234567')
u'931234567'
>>> f.clean('800123123')
u'800123123'
>>> f.clean('555555555')
Traceback (most recent call last):
...
ValidationError: [u'Enter a valid phone number in one of the formats 6XXXXXXXX, 8XXXXXXXX or 9XXXXXXXX.']
>>> f.clean('789789789')
Traceback (most recent call last):
...
ValidationError: [u'Enter a valid phone number in one of the formats 6XXXXXXXX, 8XXXXXXXX or 9XXXXXXXX.']
>>> f.clean('99123123')
Traceback (most recent call last):
...
ValidationError: [u'Enter a valid phone number in one of the formats 6XXXXXXXX, 8XXXXXXXX or 9XXXXXXXX.']
>>> f.clean('9999123123')
Traceback (most recent call last):
...
ValidationError: [u'Enter a valid phone number in one of the formats 6XXXXXXXX, 8XXXXXXXX or 9XXXXXXXX.']
>>> f.clean('')
u''

# ESIdentityCardNumberField ##############################################################

ESIdentityCardNumberField validates that data is a identification spanish code for companies or individuals (CIF, NIF or NIE).
>>> from django.contrib.localflavor.es.forms import ESIdentityCardNumberField
>>> f = ESIdentityCardNumberField()
>>> f.clean('78699688J')
'78699688J'
>>> f.clean('78699688-J')
'78699688J'
>>> f.clean('78699688 J')
'78699688J'
>>> f.clean('78699688 j')
'78699688J'
>>> f.clean('78699688T')
Traceback (most recent call last):
...
ValidationError: [u'Invalid checksum for NIF.']
>>> f.clean('X0901797J')
'X0901797J'
>>> f.clean('X-6124387-Q')
'X6124387Q'
>>> f.clean('X 0012953 G')
'X0012953G'
>>> f.clean('x-3287690-r')
'X3287690R'
>>> f.clean('t-03287690r')
'T03287690R'
>>> f.clean('X-03287690')
Traceback (most recent call last):
...
ValidationError: [u'Please enter a valid NIF, NIE, or CIF.']
>>> f.clean('X-03287690-T')
Traceback (most recent call last):
...
ValidationError: [u'Invalid checksum for NIE.']
>>> f.clean('B38790911')
'B38790911'
>>> f.clean('B31234560')
'B31234560'
>>> f.clean('B-3879091A')
'B3879091A'
>>> f.clean('B 38790917')
Traceback (most recent call last):
...
ValidationError: [u'Invalid checksum for CIF.']
>>> f.clean('B 38790911')
'B38790911'
>>> f.clean('P-3900800-H')
'P3900800H'
>>> f.clean('P 39008008')
'P39008008'
>>> f.clean('C-28795565')
'C28795565'
>>> f.clean('C 2879556E')
'C2879556E'
>>> f.clean('C28795567')
Traceback (most recent call last):
...
ValidationError: [u'Invalid checksum for CIF.']
>>> f.clean('I38790911')
Traceback (most recent call last):
...
ValidationError: [u'Please enter a valid NIF, NIE, or CIF.']
>>> f.clean('78699688-2')
Traceback (most recent call last):
...
ValidationError: [u'Please enter a valid NIF, NIE, or CIF.']
>>> f.clean('')
Traceback (most recent call last):
...
ValidationError: [u'This field is required.']

>>> f = ESIdentityCardNumberField(required=False)
>>> f.clean('78699688J')
'78699688J'
>>> f.clean('78699688-J')
'78699688J'
>>> f.clean('78699688 J')
'78699688J'
>>> f.clean('78699688 j')
'78699688J'
>>> f.clean('78699688T')
Traceback (most recent call last):
...
ValidationError: [u'Invalid checksum for NIF.']
>>> f.clean('X0901797J')
'X0901797J'
>>> f.clean('X-6124387-Q')
'X6124387Q'
>>> f.clean('X 0012953 G')
'X0012953G'
>>> f.clean('x-3287690-r')
'X3287690R'
>>> f.clean('t-03287690r')
'T03287690R'
>>> f.clean('X-03287690')
Traceback (most recent call last):
...
ValidationError: [u'Please enter a valid NIF, NIE, or CIF.']
>>> f.clean('X-03287690-T')
Traceback (most recent call last):
...
ValidationError: [u'Invalid checksum for NIE.']
>>> f.clean('B38790911')
'B38790911'
>>> f.clean('B-3879091A')
'B3879091A'
>>> f.clean('B 38790917')
Traceback (most recent call last):
...
ValidationError: [u'Invalid checksum for CIF.']
>>> f.clean('B 38790911')
'B38790911'
>>> f.clean('P-3900800-H')
'P3900800H'
>>> f.clean('P 39008008')
'P39008008'
>>> f.clean('C-28795565')
'C28795565'
>>> f.clean('C 2879556E')
'C2879556E'
>>> f.clean('C28795567')
Traceback (most recent call last):
...
ValidationError: [u'Invalid checksum for CIF.']
>>> f.clean('I38790911')
Traceback (most recent call last):
...
ValidationError: [u'Please enter a valid NIF, NIE, or CIF.']
>>> f.clean('78699688-2')
Traceback (most recent call last):
...
ValidationError: [u'Please enter a valid NIF, NIE, or CIF.']
>>> f.clean('')
u''

# ESCCCField ##############################################################

ESCCCField validates that data is a spanish bank account number (codigo cuenta cliente).

>>> from django.contrib.localflavor.es.forms import ESCCCField
>>> f = ESCCCField()
>>> f.clean('20770338793100254321')
'20770338793100254321'
>>> f.clean('2077 0338 79 3100254321')
'2077 0338 79 3100254321'
>>> f.clean('2077-0338-79-3100254321')
'2077-0338-79-3100254321'
>>> f.clean('2077.0338.79.3100254321')
Traceback (most recent call last):
...
ValidationError: [u'Please enter a valid bank account number in format XXXX-XXXX-XX-XXXXXXXXXX.']
>>> f.clean('2077-0338-78-3100254321')
Traceback (most recent call last):
...
ValidationError: [u'Invalid checksum for bank account number.']
>>> f.clean('2077-0338-89-3100254321')
Traceback (most recent call last):
...
ValidationError: [u'Invalid checksum for bank account number.']
>>> f.clean('2077-03-3879-3100254321')
Traceback (most recent call last):
...
ValidationError: [u'Please enter a valid bank account number in format XXXX-XXXX-XX-XXXXXXXXXX.']
>>> f.clean('')
Traceback (most recent call last):
...
ValidationError: [u'This field is required.']

>>> f = ESCCCField(required=False)
>>> f.clean('20770338793100254321')
'20770338793100254321'
>>> f.clean('2077 0338 79 3100254321')
'2077 0338 79 3100254321'
>>> f.clean('2077-0338-79-3100254321')
'2077-0338-79-3100254321'
>>> f.clean('2077.0338.79.3100254321')
Traceback (most recent call last):
...
ValidationError: [u'Please enter a valid bank account number in format XXXX-XXXX-XX-XXXXXXXXXX.']
>>> f.clean('2077-0338-78-3100254321')
Traceback (most recent call last):
...
ValidationError: [u'Invalid checksum for bank account number.']
>>> f.clean('2077-0338-89-3100254321')
Traceback (most recent call last):
...
ValidationError: [u'Invalid checksum for bank account number.']
>>> f.clean('2077-03-3879-3100254321')
Traceback (most recent call last):
...
ValidationError: [u'Please enter a valid bank account number in format XXXX-XXXX-XX-XXXXXXXXXX.']
>>> f.clean('')
u''

# ESRegionSelect ##############################################################

ESRegionSelect is a Select widget that uses a list of Spain regions as its choices.
>>> from django.contrib.localflavor.es.forms import ESRegionSelect
>>> w = ESRegionSelect()
>>> w.render('regions', 'CT')
u'<select name="regions">\n<option value="AN">Andalusia</option>\n<option value="AR">Aragon</option>\n<option value="O">Principality of Asturias</option>\n<option value="IB">Balearic Islands</option>\n<option value="PV">Basque Country</option>\n<option value="CN">Canary Islands</option>\n<option value="S">Cantabria</option>\n<option value="CM">Castile-La Mancha</option>\n<option value="CL">Castile and Leon</option>\n<option value="CT" selected="selected">Catalonia</option>\n<option value="EX">Extremadura</option>\n<option value="GA">Galicia</option>\n<option value="LO">La Rioja</option>\n<option value="M">Madrid</option>\n<option value="MU">Region of Murcia</option>\n<option value="NA">Foral Community of Navarre</option>\n<option value="VC">Valencian Community</option>\n</select>'

# ESProvincenSelect ##############################################################

ESProvinceSelect is a Select widget that uses a list of Spain provinces as its choices.
>>> from django.contrib.localflavor.es.forms import ESProvinceSelect
>>> w = ESProvinceSelect()
>>> w.render('provinces', '08')
u'<select name="provinces">\n<option value="01">Arava</option>\n<option value="02">Albacete</option>\n<option value="03">Alacant</option>\n<option value="04">Almeria</option>\n<option value="05">Avila</option>\n<option value="06">Badajoz</option>\n<option value="07">Illes Balears</option>\n<option value="08" selected="selected">Barcelona</option>\n<option value="09">Burgos</option>\n<option value="10">Caceres</option>\n<option value="11">Cadiz</option>\n<option value="12">Castello</option>\n<option value="13">Ciudad Real</option>\n<option value="14">Cordoba</option>\n<option value="15">A Coruna</option>\n<option value="16">Cuenca</option>\n<option value="17">Girona</option>\n<option value="18">Granada</option>\n<option value="19">Guadalajara</option>\n<option value="20">Guipuzkoa</option>\n<option value="21">Huelva</option>\n<option value="22">Huesca</option>\n<option value="23">Jaen</option>\n<option value="24">Leon</option>\n<option value="25">Lleida</option>\n<option value="26">La Rioja</option>\n<option value="27">Lugo</option>\n<option value="28">Madrid</option>\n<option value="29">Malaga</option>\n<option value="30">Murcia</option>\n<option value="31">Navarre</option>\n<option value="32">Ourense</option>\n<option value="33">Asturias</option>\n<option value="34">Palencia</option>\n<option value="35">Las Palmas</option>\n<option value="36">Pontevedra</option>\n<option value="37">Salamanca</option>\n<option value="38">Santa Cruz de Tenerife</option>\n<option value="39">Cantabria</option>\n<option value="40">Segovia</option>\n<option value="41">Seville</option>\n<option value="42">Soria</option>\n<option value="43">Tarragona</option>\n<option value="44">Teruel</option>\n<option value="45">Toledo</option>\n<option value="46">Valencia</option>\n<option value="47">Valladolid</option>\n<option value="48">Bizkaia</option>\n<option value="49">Zamora</option>\n<option value="50">Zaragoza</option>\n<option value="51">Ceuta</option>\n<option value="52">Melilla</option>\n</select>'

"""

