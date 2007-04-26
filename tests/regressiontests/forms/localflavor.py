# -*- coding: utf-8 -*-
# Tests for the different contrib/localflavor/ form fields.

localflavor_tests = r"""
# USZipCodeField ##############################################################

USZipCodeField validates that the data is either a five-digit U.S. zip code or
a zip+4.
>>> from django.contrib.localflavor.us.forms import USZipCodeField
>>> f = USZipCodeField()
>>> f.clean('60606')
u'60606'
>>> f.clean(60606)
u'60606'
>>> f.clean('04000')
u'04000'
>>> f.clean('4000')
Traceback (most recent call last):
...
ValidationError: [u'Enter a zip code in the format XXXXX or XXXXX-XXXX.']
>>> f.clean('60606-1234')
u'60606-1234'
>>> f.clean('6060-1234')
Traceback (most recent call last):
...
ValidationError: [u'Enter a zip code in the format XXXXX or XXXXX-XXXX.']
>>> f.clean('60606-')
Traceback (most recent call last):
...
ValidationError: [u'Enter a zip code in the format XXXXX or XXXXX-XXXX.']
>>> f.clean(None)
Traceback (most recent call last):
...
ValidationError: [u'This field is required.']
>>> f.clean('')
Traceback (most recent call last):
...
ValidationError: [u'This field is required.']

>>> f = USZipCodeField(required=False)
>>> f.clean('60606')
u'60606'
>>> f.clean(60606)
u'60606'
>>> f.clean('04000')
u'04000'
>>> f.clean('4000')
Traceback (most recent call last):
...
ValidationError: [u'Enter a zip code in the format XXXXX or XXXXX-XXXX.']
>>> f.clean('60606-1234')
u'60606-1234'
>>> f.clean('6060-1234')
Traceback (most recent call last):
...
ValidationError: [u'Enter a zip code in the format XXXXX or XXXXX-XXXX.']
>>> f.clean('60606-')
Traceback (most recent call last):
...
ValidationError: [u'Enter a zip code in the format XXXXX or XXXXX-XXXX.']
>>> f.clean(None)
u''
>>> f.clean('')
u''

# USPhoneNumberField ##########################################################

USPhoneNumberField validates that the data is a valid U.S. phone number,
including the area code. It's normalized to XXX-XXX-XXXX format.
>>> from django.contrib.localflavor.us.forms import USPhoneNumberField
>>> f = USPhoneNumberField()
>>> f.clean('312-555-1212')
u'312-555-1212'
>>> f.clean('3125551212')
u'312-555-1212'
>>> f.clean('312 555-1212')
u'312-555-1212'
>>> f.clean('(312) 555-1212')
u'312-555-1212'
>>> f.clean('312 555 1212')
u'312-555-1212'
>>> f.clean('312.555.1212')
u'312-555-1212'
>>> f.clean('312.555-1212')
u'312-555-1212'
>>> f.clean(' (312) 555.1212 ')
u'312-555-1212'
>>> f.clean('555-1212')
Traceback (most recent call last):
...
ValidationError: [u'Phone numbers must be in XXX-XXX-XXXX format.']
>>> f.clean('312-55-1212')
Traceback (most recent call last):
...
ValidationError: [u'Phone numbers must be in XXX-XXX-XXXX format.']
>>> f.clean(None)
Traceback (most recent call last):
...
ValidationError: [u'This field is required.']
>>> f.clean('')
Traceback (most recent call last):
...
ValidationError: [u'This field is required.']

>>> f = USPhoneNumberField(required=False)
>>> f.clean('312-555-1212')
u'312-555-1212'
>>> f.clean('3125551212')
u'312-555-1212'
>>> f.clean('312 555-1212')
u'312-555-1212'
>>> f.clean('(312) 555-1212')
u'312-555-1212'
>>> f.clean('312 555 1212')
u'312-555-1212'
>>> f.clean('312.555.1212')
u'312-555-1212'
>>> f.clean('312.555-1212')
u'312-555-1212'
>>> f.clean(' (312) 555.1212 ')
u'312-555-1212'
>>> f.clean('555-1212')
Traceback (most recent call last):
...
ValidationError: [u'Phone numbers must be in XXX-XXX-XXXX format.']
>>> f.clean('312-55-1212')
Traceback (most recent call last):
...
ValidationError: [u'Phone numbers must be in XXX-XXX-XXXX format.']
>>> f.clean(None)
u''
>>> f.clean('')
u''

# USStateField ################################################################

USStateField validates that the data is either an abbreviation or name of a
U.S. state.
>>> from django.contrib.localflavor.us.forms import USStateField
>>> f = USStateField()
>>> f.clean('il')
u'IL'
>>> f.clean('IL')
u'IL'
>>> f.clean('illinois')
u'IL'
>>> f.clean('  illinois ')
u'IL'
>>> f.clean(60606)
Traceback (most recent call last):
...
ValidationError: [u'Enter a U.S. state or territory.']
>>> f.clean(None)
Traceback (most recent call last):
...
ValidationError: [u'This field is required.']
>>> f.clean('')
Traceback (most recent call last):
...
ValidationError: [u'This field is required.']

>>> f = USStateField(required=False)
>>> f.clean('il')
u'IL'
>>> f.clean('IL')
u'IL'
>>> f.clean('illinois')
u'IL'
>>> f.clean('  illinois ')
u'IL'
>>> f.clean(60606)
Traceback (most recent call last):
...
ValidationError: [u'Enter a U.S. state or territory.']
>>> f.clean(None)
u''
>>> f.clean('')
u''

# USStateSelect ###############################################################

USStateSelect is a Select widget that uses a list of U.S. states/territories
as its choices.
>>> from django.contrib.localflavor.us.forms import USStateSelect
>>> w = USStateSelect()
>>> print w.render('state', 'IL')
<select name="state">
<option value="AL">Alabama</option>
<option value="AK">Alaska</option>
<option value="AS">American Samoa</option>
<option value="AZ">Arizona</option>
<option value="AR">Arkansas</option>
<option value="CA">California</option>
<option value="CO">Colorado</option>
<option value="CT">Connecticut</option>
<option value="DE">Delaware</option>
<option value="DC">District of Columbia</option>
<option value="FM">Federated States of Micronesia</option>
<option value="FL">Florida</option>
<option value="GA">Georgia</option>
<option value="GU">Guam</option>
<option value="HI">Hawaii</option>
<option value="ID">Idaho</option>
<option value="IL" selected="selected">Illinois</option>
<option value="IN">Indiana</option>
<option value="IA">Iowa</option>
<option value="KS">Kansas</option>
<option value="KY">Kentucky</option>
<option value="LA">Louisiana</option>
<option value="ME">Maine</option>
<option value="MH">Marshall Islands</option>
<option value="MD">Maryland</option>
<option value="MA">Massachusetts</option>
<option value="MI">Michigan</option>
<option value="MN">Minnesota</option>
<option value="MS">Mississippi</option>
<option value="MO">Missouri</option>
<option value="MT">Montana</option>
<option value="NE">Nebraska</option>
<option value="NV">Nevada</option>
<option value="NH">New Hampshire</option>
<option value="NJ">New Jersey</option>
<option value="NM">New Mexico</option>
<option value="NY">New York</option>
<option value="NC">North Carolina</option>
<option value="ND">North Dakota</option>
<option value="MP">Northern Mariana Islands</option>
<option value="OH">Ohio</option>
<option value="OK">Oklahoma</option>
<option value="OR">Oregon</option>
<option value="PW">Palau</option>
<option value="PA">Pennsylvania</option>
<option value="PR">Puerto Rico</option>
<option value="RI">Rhode Island</option>
<option value="SC">South Carolina</option>
<option value="SD">South Dakota</option>
<option value="TN">Tennessee</option>
<option value="TX">Texas</option>
<option value="UT">Utah</option>
<option value="VT">Vermont</option>
<option value="VI">Virgin Islands</option>
<option value="VA">Virginia</option>
<option value="WA">Washington</option>
<option value="WV">West Virginia</option>
<option value="WI">Wisconsin</option>
<option value="WY">Wyoming</option>
</select>

# USSocialSecurityNumberField #################################################
>>> from django.contrib.localflavor.us.forms import USSocialSecurityNumberField
>>> f = USSocialSecurityNumberField()
>>> f.clean('987-65-4330')
u'987-65-4330'
>>> f.clean('987654330')
u'987-65-4330'
>>> f.clean('078-05-1120')
Traceback (most recent call last):
...
ValidationError: [u'Enter a valid U.S. Social Security number in XXX-XX-XXXX format.']

# UKPostcodeField #############################################################

UKPostcodeField validates that the data is a valid UK postcode.
>>> from django.contrib.localflavor.uk.forms import UKPostcodeField
>>> f = UKPostcodeField()
>>> f.clean('BT32 4PX')
u'BT32 4PX'
>>> f.clean('GIR 0AA')
u'GIR 0AA'
>>> f.clean('BT324PX')
Traceback (most recent call last):
...
ValidationError: [u'Enter a postcode. A space is required between the two postcode parts.']
>>> f.clean('1NV 4L1D')
Traceback (most recent call last):
...
ValidationError: [u'Enter a postcode. A space is required between the two postcode parts.']
>>> f.clean(None)
Traceback (most recent call last):
...
ValidationError: [u'This field is required.']
>>> f.clean('')
Traceback (most recent call last):
...
ValidationError: [u'This field is required.']

>>> f = UKPostcodeField(required=False)
>>> f.clean('BT32 4PX')
u'BT32 4PX'
>>> f.clean('GIR 0AA')
u'GIR 0AA'
>>> f.clean('1NV 4L1D')
Traceback (most recent call last):
...
ValidationError: [u'Enter a postcode. A space is required between the two postcode parts.']
>>> f.clean('BT324PX')
Traceback (most recent call last):
...
ValidationError: [u'Enter a postcode. A space is required between the two postcode parts.']
>>> f.clean(None)
u''
>>> f.clean('')
u''

# FRZipCodeField #############################################################

FRZipCodeField validates that the data is a valid FR zipcode.
>>> from django.contrib.localflavor.fr.forms import FRZipCodeField
>>> f = FRZipCodeField()
>>> f.clean('75001')
u'75001'
>>> f.clean('93200')
u'93200'
>>> f.clean('2A200')
Traceback (most recent call last):
...
ValidationError: [u'Enter a zip code in the format XXXXX.']
>>> f.clean('980001')
Traceback (most recent call last):
...
ValidationError: [u'Enter a zip code in the format XXXXX.']
>>> f.clean(None)
Traceback (most recent call last):
...
ValidationError: [u'This field is required.']
>>> f.clean('')
Traceback (most recent call last):
...
ValidationError: [u'This field is required.']

>>> f = FRZipCodeField(required=False)
>>> f.clean('75001')
u'75001'
>>> f.clean('93200')
u'93200'
>>> f.clean('2A200')
Traceback (most recent call last):
...
ValidationError: [u'Enter a zip code in the format XXXXX.']
>>> f.clean('980001')
Traceback (most recent call last):
...
ValidationError: [u'Enter a zip code in the format XXXXX.']
>>> f.clean(None)
u''
>>> f.clean('')
u''


# FRPhoneNumberField ##########################################################

FRPhoneNumberField validates that the data is a valid french phone number.
It's normalized to 0X XX XX XX XX format. Dots are valid too.
>>> from django.contrib.localflavor.fr.forms import FRPhoneNumberField
>>> f = FRPhoneNumberField()
>>> f.clean('01 55 44 58 64')
u'01 55 44 58 64'
>>> f.clean('0155445864')
u'01 55 44 58 64'
>>> f.clean('01 5544 5864')
u'01 55 44 58 64'
>>> f.clean('01 55.44.58.64')
u'01 55 44 58 64'
>>> f.clean('01.55.44.58.64')
u'01 55 44 58 64'
>>> f.clean('01,55,44,58,64')
Traceback (most recent call last):
...
ValidationError: [u'Phone numbers must be in 0X XX XX XX XX format.']
>>> f.clean('555 015 544')
Traceback (most recent call last):
...
ValidationError: [u'Phone numbers must be in 0X XX XX XX XX format.']
>>> f.clean(None)
Traceback (most recent call last):
...
ValidationError: [u'This field is required.']
>>> f.clean('')
Traceback (most recent call last):
...
ValidationError: [u'This field is required.']

>>> f = FRPhoneNumberField(required=False)
>>> f.clean('01 55 44 58 64')
u'01 55 44 58 64'
>>> f.clean('0155445864')
u'01 55 44 58 64'
>>> f.clean('01 5544 5864')
u'01 55 44 58 64'
>>> f.clean('01 55.44.58.64')
u'01 55 44 58 64'
>>> f.clean('01.55.44.58.64')
u'01 55 44 58 64'
>>> f.clean('01,55,44,58,64')
Traceback (most recent call last):
...
ValidationError: [u'Phone numbers must be in 0X XX XX XX XX format.']
>>> f.clean('555 015 544')
Traceback (most recent call last):
...
ValidationError: [u'Phone numbers must be in 0X XX XX XX XX format.']
>>> f.clean(None)
u''
>>> f.clean('')
u''

# FRDepartmentSelect ###############################################################

FRDepartmentSelect is a Select widget that uses a list of french departments
including DOM TOM
>>> from django.contrib.localflavor.fr.forms import FRDepartmentSelect
>>> w = FRDepartmentSelect()
>>> print w.render('dep', 'Paris')
<select name="dep">
<option value="01">01 - Ain</option>
<option value="02">02 - Aisne</option>
<option value="03">03 - Allier</option>
<option value="04">04 - Alpes-de-Haute-Provence</option>
<option value="05">05 - Hautes-Alpes</option>
<option value="06">06 - Alpes-Maritimes</option>
<option value="07">07 - Ardeche</option>
<option value="08">08 - Ardennes</option>
<option value="09">09 - Ariege</option>
<option value="10">10 - Aube</option>
<option value="11">11 - Aude</option>
<option value="12">12 - Aveyron</option>
<option value="13">13 - Bouches-du-Rhone</option>
<option value="14">14 - Calvados</option>
<option value="15">15 - Cantal</option>
<option value="16">16 - Charente</option>
<option value="17">17 - Charente-Maritime</option>
<option value="18">18 - Cher</option>
<option value="19">19 - Correze</option>
<option value="21">21 - Cote-d&#39;Or</option>
<option value="22">22 - Cotes-d&#39;Armor</option>
<option value="23">23 - Creuse</option>
<option value="24">24 - Dordogne</option>
<option value="25">25 - Doubs</option>
<option value="26">26 - Drome</option>
<option value="27">27 - Eure</option>
<option value="28">28 - Eure-et-Loire</option>
<option value="29">29 - Finistere</option>
<option value="2A">2A - Corse-du-Sud</option>
<option value="2B">2B - Haute-Corse</option>
<option value="30">30 - Gard</option>
<option value="31">31 - Haute-Garonne</option>
<option value="32">32 - Gers</option>
<option value="33">33 - Gironde</option>
<option value="34">34 - Herault</option>
<option value="35">35 - Ille-et-Vilaine</option>
<option value="36">36 - Indre</option>
<option value="37">37 - Indre-et-Loire</option>
<option value="38">38 - Isere</option>
<option value="39">39 - Jura</option>
<option value="40">40 - Landes</option>
<option value="41">41 - Loir-et-Cher</option>
<option value="42">42 - Loire</option>
<option value="43">43 - Haute-Loire</option>
<option value="44">44 - Loire-Atlantique</option>
<option value="45">45 - Loiret</option>
<option value="46">46 - Lot</option>
<option value="47">47 - Lot-et-Garonne</option>
<option value="48">48 - Lozere</option>
<option value="49">49 - Maine-et-Loire</option>
<option value="50">50 - Manche</option>
<option value="51">51 - Marne</option>
<option value="52">52 - Haute-Marne</option>
<option value="53">53 - Mayenne</option>
<option value="54">54 - Meurthe-et-Moselle</option>
<option value="55">55 - Meuse</option>
<option value="56">56 - Morbihan</option>
<option value="57">57 - Moselle</option>
<option value="58">58 - Nievre</option>
<option value="59">59 - Nord</option>
<option value="60">60 - Oise</option>
<option value="61">61 - Orne</option>
<option value="62">62 - Pas-de-Calais</option>
<option value="63">63 - Puy-de-Dome</option>
<option value="64">64 - Pyrenees-Atlantiques</option>
<option value="65">65 - Hautes-Pyrenees</option>
<option value="66">66 - Pyrenees-Orientales</option>
<option value="67">67 - Bas-Rhin</option>
<option value="68">68 - Haut-Rhin</option>
<option value="69">69 - Rhone</option>
<option value="70">70 - Haute-Saone</option>
<option value="71">71 - Saone-et-Loire</option>
<option value="72">72 - Sarthe</option>
<option value="73">73 - Savoie</option>
<option value="74">74 - Haute-Savoie</option>
<option value="75">75 - Paris</option>
<option value="76">76 - Seine-Maritime</option>
<option value="77">77 - Seine-et-Marne</option>
<option value="78">78 - Yvelines</option>
<option value="79">79 - Deux-Sevres</option>
<option value="80">80 - Somme</option>
<option value="81">81 - Tarn</option>
<option value="82">82 - Tarn-et-Garonne</option>
<option value="83">83 - Var</option>
<option value="84">84 - Vaucluse</option>
<option value="85">85 - Vendee</option>
<option value="86">86 - Vienne</option>
<option value="87">87 - Haute-Vienne</option>
<option value="88">88 - Vosges</option>
<option value="89">89 - Yonne</option>
<option value="90">90 - Territoire de Belfort</option>
<option value="91">91 - Essonne</option>
<option value="92">92 - Hauts-de-Seine</option>
<option value="93">93 - Seine-Saint-Denis</option>
<option value="94">94 - Val-de-Marne</option>
<option value="95">95 - Val-d&#39;Oise</option>
<option value="2A">2A - Corse du sud</option>
<option value="2B">2B - Haute Corse</option>
<option value="971">971 - Guadeloupe</option>
<option value="972">972 - Martinique</option>
<option value="973">973 - Guyane</option>
<option value="974">974 - La Reunion</option>
<option value="975">975 - Saint-Pierre-et-Miquelon</option>
<option value="976">976 - Mayotte</option>
<option value="984">984 - Terres Australes et Antarctiques</option>
<option value="986">986 - Wallis et Futuna</option>
<option value="987">987 - Polynesie Francaise</option>
<option value="988">988 - Nouvelle-Caledonie</option>
</select>

# JPPostalCodeField ###############################################################

A form field that validates its input is a Japanese postcode.

Accepts 7 digits(with/out hyphen).
>>> from django.contrib.localflavor.jp.forms import JPPostalCodeField
>>> f = JPPostalCodeField()
>>> f.clean('251-0032')
u'2510032'
>>> f.clean('2510032')
u'2510032'
>>> f.clean('2510-032')
Traceback (most recent call last):
...
ValidationError: [u'Enter a postal code in the format XXXXXXX or XXX-XXXX.']
>>> f.clean('251a0032')
Traceback (most recent call last):
...
ValidationError: [u'Enter a postal code in the format XXXXXXX or XXX-XXXX.']
>>> f.clean('a51-0032')
Traceback (most recent call last):
...
ValidationError: [u'Enter a postal code in the format XXXXXXX or XXX-XXXX.']
>>> f.clean('25100321')
Traceback (most recent call last):
...
ValidationError: [u'Enter a postal code in the format XXXXXXX or XXX-XXXX.']
>>> f.clean('')
Traceback (most recent call last):
...
ValidationError: [u'This field is required.']

>>> f = JPPostalCodeField(required=False)
>>> f.clean('251-0032')
u'2510032'
>>> f.clean('2510032')
u'2510032'
>>> f.clean('2510-032')
Traceback (most recent call last):
...
ValidationError: [u'Enter a postal code in the format XXXXXXX or XXX-XXXX.']
>>> f.clean('')
u''
>>> f.clean(None)
u''

# JPPrefectureSelect ###############################################################

A Select widget that uses a list of Japanese prefectures as its choices.
>>> from django.contrib.localflavor.jp.forms import JPPrefectureSelect
>>> w = JPPrefectureSelect()
>>> print w.render('prefecture', 'kanagawa')
<select name="prefecture">
<option value="hokkaido">Hokkaido</option>
<option value="aomori">Aomori</option>
<option value="iwate">Iwate</option>
<option value="miyagi">Miyagi</option>
<option value="akita">Akita</option>
<option value="yamagata">Yamagata</option>
<option value="fukushima">Fukushima</option>
<option value="ibaraki">Ibaraki</option>
<option value="tochigi">Tochigi</option>
<option value="gunma">Gunma</option>
<option value="saitama">Saitama</option>
<option value="chiba">Chiba</option>
<option value="tokyo">Tokyo</option>
<option value="kanagawa" selected="selected">Kanagawa</option>
<option value="yamanashi">Yamanashi</option>
<option value="nagano">Nagano</option>
<option value="niigata">Niigata</option>
<option value="toyama">Toyama</option>
<option value="ishikawa">Ishikawa</option>
<option value="fukui">Fukui</option>
<option value="gifu">Gifu</option>
<option value="shizuoka">Shizuoka</option>
<option value="aichi">Aichi</option>
<option value="mie">Mie</option>
<option value="shiga">Shiga</option>
<option value="kyoto">Kyoto</option>
<option value="osaka">Osaka</option>
<option value="hyogo">Hyogo</option>
<option value="nara">Nara</option>
<option value="wakayama">Wakayama</option>
<option value="tottori">Tottori</option>
<option value="shimane">Shimane</option>
<option value="okayama">Okayama</option>
<option value="hiroshima">Hiroshima</option>
<option value="yamaguchi">Yamaguchi</option>
<option value="tokushima">Tokushima</option>
<option value="kagawa">Kagawa</option>
<option value="ehime">Ehime</option>
<option value="kochi">Kochi</option>
<option value="fukuoka">Fukuoka</option>
<option value="saga">Saga</option>
<option value="nagasaki">Nagasaki</option>
<option value="kumamoto">Kumamoto</option>
<option value="oita">Oita</option>
<option value="miyazaki">Miyazaki</option>
<option value="kagoshima">Kagoshima</option>
<option value="okinawa">Okinawa</option>
</select>

# ITZipCodeField #############################################################

>>> from django.contrib.localflavor.it.forms import ITZipCodeField
>>> f = ITZipCodeField()
>>> f.clean('00100')
u'00100'
>>> f.clean(' 00100')
Traceback (most recent call last):
...
ValidationError: [u'Enter a valid zip code.']

# ITRegionSelect #############################################################

>>> from django.contrib.localflavor.it.forms import ITRegionSelect
>>> w = ITRegionSelect()
>>> w.render('regions', 'PMN')
u'<select name="regions">\n<option value="ABR">Abruzzo</option>\n<option value="BAS">Basilicata</option>\n<option value="CAL">Calabria</option>\n<option value="CAM">Campania</option>\n<option value="EMR">Emilia-Romagna</option>\n<option value="FVG">Friuli-Venezia Giulia</option>\n<option value="LAZ">Lazio</option>\n<option value="LIG">Liguria</option>\n<option value="LOM">Lombardia</option>\n<option value="MAR">Marche</option>\n<option value="MOL">Molise</option>\n<option value="PMN" selected="selected">Piemonte</option>\n<option value="PUG">Puglia</option>\n<option value="SAR">Sardegna</option>\n<option value="SIC">Sicilia</option>\n<option value="TOS">Toscana</option>\n<option value="TAA">Trentino-Alto Adige</option>\n<option value="UMB">Umbria</option>\n<option value="VAO">Valle d\u2019Aosta</option>\n<option value="VEN">Veneto</option>\n</select>'

# ITSocialSecurityNumberField #################################################

>>> from django.contrib.localflavor.it.forms import ITSocialSecurityNumberField
>>> f = ITSocialSecurityNumberField()
>>> f.clean('LVSGDU99T71H501L')
u'LVSGDU99T71H501L'
>>> f.clean('LBRRME11A01L736W')
u'LBRRME11A01L736W'
>>> f.clean('lbrrme11a01l736w')
u'LBRRME11A01L736W'
>>> f.clean('LBR RME 11A01 L736W')
u'LBRRME11A01L736W'
>>> f.clean('LBRRME11A01L736A')
Traceback (most recent call last):
...
ValidationError: [u'Enter a valid Social Security number.']
>>> f.clean('%BRRME11A01L736W')
Traceback (most recent call last):
...
ValidationError: [u'Enter a valid Social Security number.']

# ITVatNumberField ###########################################################

>>> from django.contrib.localflavor.it.forms import ITVatNumberField
>>> f = ITVatNumberField()
>>> f.clean('07973780013')
u'07973780013'
>>> f.clean('7973780013')
u'07973780013'
>>> f.clean(7973780013)
u'07973780013'
>>> f.clean('07973780014')
Traceback (most recent call last):
...
ValidationError: [u'Enter a valid VAT number.']
>>> f.clean('A7973780013')
Traceback (most recent call last):
...
ValidationError: [u'Enter a valid VAT number.']

# FIZipCodeField #############################################################

FIZipCodeField validates that the data is a valid FI zipcode.
>>> from django.contrib.localflavor.fi.forms import FIZipCodeField
>>> f = FIZipCodeField()
>>> f.clean('20540')
u'20540'
>>> f.clean('20101')
u'20101'
>>> f.clean('20s40')
Traceback (most recent call last):
...
ValidationError: [u'Enter a zip code in the format XXXXX.']
>>> f.clean('205401')
Traceback (most recent call last):
...
ValidationError: [u'Enter a zip code in the format XXXXX.']
>>> f.clean(None)
Traceback (most recent call last):
...
ValidationError: [u'This field is required.']
>>> f.clean('')
Traceback (most recent call last):
...
ValidationError: [u'This field is required.']

>>> f = FIZipCodeField(required=False)
>>> f.clean('20540')
u'20540'
>>> f.clean('20101')
u'20101'
>>> f.clean('20s40')
Traceback (most recent call last):
...
ValidationError: [u'Enter a zip code in the format XXXXX.']
>>> f.clean('205401')
Traceback (most recent call last):
...
ValidationError: [u'Enter a zip code in the format XXXXX.']
>>> f.clean(None)
u''
>>> f.clean('')
u''

# FIMunicipalitySelect ###############################################################

A Select widget that uses a list of Finnish municipalities as its choices.
>>> from django.contrib.localflavor.fi.forms import FIMunicipalitySelect
>>> w = FIMunicipalitySelect()
>>> unicode(w.render('municipalities', 'turku'))
u'<select name="municipalities">\n<option value="akaa">Akaa</option>\n<option value="alaharma">Alah\xe4rm\xe4</option>\n<option value="alajarvi">Alaj\xe4rvi</option>\n<option value="alastaro">Alastaro</option>\n<option value="alavieska">Alavieska</option>\n<option value="alavus">Alavus</option>\n<option value="anjalankoski">Anjalankoski</option>\n<option value="artjarvi">Artj\xe4rvi</option>\n<option value="asikkala">Asikkala</option>\n<option value="askainen">Askainen</option>\n<option value="askola">Askola</option>\n<option value="aura">Aura</option>\n<option value="brando">Br\xe4nd\xf6</option>\n<option value="dragsfjard">Dragsfj\xe4rd</option>\n<option value="eckero">Ecker\xf6</option>\n<option value="elimaki">Elim\xe4ki</option>\n<option value="eno">Eno</option>\n<option value="enonkoski">Enonkoski</option>\n<option value="enontekio">Enonteki\xf6</option>\n<option value="espoo">Espoo</option>\n<option value="eura">Eura</option>\n<option value="eurajoki">Eurajoki</option>\n<option value="evijarvi">Evij\xe4rvi</option>\n<option value="finstrom">Finstr\xf6m</option>\n<option value="forssa">Forssa</option>\n<option value="foglo">F\xf6gl\xf6</option>\n<option value="geta">Geta</option>\n<option value="haapajarvi">Haapaj\xe4rvi</option>\n<option value="haapavesi">Haapavesi</option>\n<option value="hailuoto">Hailuoto</option>\n<option value="halikko">Halikko</option>\n<option value="halsua">Halsua</option>\n<option value="hamina">Hamina</option>\n<option value="hammarland">Hammarland</option>\n<option value="hankasalmi">Hankasalmi</option>\n<option value="hanko">Hanko</option>\n<option value="harjavalta">Harjavalta</option>\n<option value="hartola">Hartola</option>\n<option value="hattula">Hattula</option>\n<option value="hauho">Hauho</option>\n<option value="haukipudas">Haukipudas</option>\n<option value="hausjarvi">Hausj\xe4rvi</option>\n<option value="heinola">Heinola</option>\n<option value="heinavesi">Hein\xe4vesi</option>\n<option value="helsinki">Helsinki</option>\n<option value="himanka">Himanka</option>\n<option value="hirvensalmi">Hirvensalmi</option>\n<option value="hollola">Hollola</option>\n<option value="honkajoki">Honkajoki</option>\n<option value="houtskari">Houtskari</option>\n<option value="huittinen">Huittinen</option>\n<option value="humppila">Humppila</option>\n<option value="hyrynsalmi">Hyrynsalmi</option>\n<option value="hyvinkaa">Hyvink\xe4\xe4</option>\n<option value="hameenkoski">H\xe4meenkoski</option>\n<option value="hameenkyro">H\xe4meenkyr\xf6</option>\n<option value="hameenlinna">H\xe4meenlinna</option>\n<option value="ii">Ii</option>\n<option value="iisalmi">Iisalmi</option>\n<option value="iitti">Iitti</option>\n<option value="ikaalinen">Ikaalinen</option>\n<option value="ilmajoki">Ilmajoki</option>\n<option value="ilomantsi">Ilomantsi</option>\n<option value="imatra">Imatra</option>\n<option value="inari">Inari</option>\n<option value="inio">Ini\xf6</option>\n<option value="inkoo">Inkoo</option>\n<option value="isojoki">Isojoki</option>\n<option value="isokyro">Isokyr\xf6</option>\n<option value="jaala">Jaala</option>\n<option value="jalasjarvi">Jalasj\xe4rvi</option>\n<option value="janakkala">Janakkala</option>\n<option value="joensuu">Joensuu</option>\n<option value="jokioinen">Jokioinen</option>\n<option value="jomala">Jomala</option>\n<option value="joroinen">Joroinen</option>\n<option value="joutsa">Joutsa</option>\n<option value="joutseno">Joutseno</option>\n<option value="juankoski">Juankoski</option>\n<option value="jurva">Jurva</option>\n<option value="juuka">Juuka</option>\n<option value="juupajoki">Juupajoki</option>\n<option value="juva">Juva</option>\n<option value="jyvaskyla">Jyv\xe4skyl\xe4</option>\n<option value="jyvaskylan_mlk">Jyv\xe4skyl\xe4n maalaiskunta</option>\n<option value="jamijarvi">J\xe4mij\xe4rvi</option>\n<option value="jamsa">J\xe4ms\xe4</option>\n<option value="jamsankoski">J\xe4ms\xe4nkoski</option>\n<option value="jarvenpaa">J\xe4rvenp\xe4\xe4</option>\n<option value="kaarina">Kaarina</option>\n<option value="kaavi">Kaavi</option>\n<option value="kajaani">Kajaani</option>\n<option value="kalajoki">Kalajoki</option>\n<option value="kalvola">Kalvola</option>\n<option value="kangasala">Kangasala</option>\n<option value="kangasniemi">Kangasniemi</option>\n<option value="kankaanpaa">Kankaanp\xe4\xe4</option>\n<option value="kannonkoski">Kannonkoski</option>\n<option value="kannus">Kannus</option>\n<option value="karijoki">Karijoki</option>\n<option value="karjaa">Karjaa</option>\n<option value="karjalohja">Karjalohja</option>\n<option value="karkkila">Karkkila</option>\n<option value="karstula">Karstula</option>\n<option value="karttula">Karttula</option>\n<option value="karvia">Karvia</option>\n<option value="kaskinen">Kaskinen</option>\n<option value="kauhajoki">Kauhajoki</option>\n<option value="kauhava">Kauhava</option>\n<option value="kauniainen">Kauniainen</option>\n<option value="kaustinen">Kaustinen</option>\n<option value="keitele">Keitele</option>\n<option value="kemi">Kemi</option>\n<option value="kemijarvi">Kemij\xe4rvi</option>\n<option value="keminmaa">Keminmaa</option>\n<option value="kemio">Kemi\xf6</option>\n<option value="kempele">Kempele</option>\n<option value="kerava">Kerava</option>\n<option value="kerimaki">Kerim\xe4ki</option>\n<option value="kestila">Kestil\xe4</option>\n<option value="kesalahti">Kes\xe4lahti</option>\n<option value="keuruu">Keuruu</option>\n<option value="kihnio">Kihni\xf6</option>\n<option value="kiikala">Kiikala</option>\n<option value="kiikoinen">Kiikoinen</option>\n<option value="kiiminki">Kiiminki</option>\n<option value="kinnula">Kinnula</option>\n<option value="kirkkonummi">Kirkkonummi</option>\n<option value="kisko">Kisko</option>\n<option value="kitee">Kitee</option>\n<option value="kittila">Kittil\xe4</option>\n<option value="kiukainen">Kiukainen</option>\n<option value="kiuruvesi">Kiuruvesi</option>\n<option value="kivijarvi">Kivij\xe4rvi</option>\n<option value="kokemaki">Kokem\xe4ki</option>\n<option value="kokkola">Kokkola</option>\n<option value="kolari">Kolari</option>\n<option value="konnevesi">Konnevesi</option>\n<option value="kontiolahti">Kontiolahti</option>\n<option value="korpilahti">Korpilahti</option>\n<option value="korppoo">Korppoo</option>\n<option value="korsnas">Korsn\xe4s</option>\n<option value="kortesjarvi">Kortesj\xe4rvi</option>\n<option value="koskitl">KoskiTl</option>\n<option value="kotka">Kotka</option>\n<option value="kouvola">Kouvola</option>\n<option value="kristiinankaupunki">Kristiinankaupunki</option>\n<option value="kruunupyy">Kruunupyy</option>\n<option value="kuhmalahti">Kuhmalahti</option>\n<option value="kuhmo">Kuhmo</option>\n<option value="kuhmoinen">Kuhmoinen</option>\n<option value="kumlinge">Kumlinge</option>\n<option value="kuopio">Kuopio</option>\n<option value="kuortane">Kuortane</option>\n<option value="kurikka">Kurikka</option>\n<option value="kuru">Kuru</option>\n<option value="kustavi">Kustavi</option>\n<option value="kuusamo">Kuusamo</option>\n<option value="kuusankoski">Kuusankoski</option>\n<option value="kuusjoki">Kuusjoki</option>\n<option value="kylmakoski">Kylm\xe4koski</option>\n<option value="kyyjarvi">Kyyj\xe4rvi</option>\n<option value="kalvia">K\xe4lvi\xe4</option>\n<option value="karkola">K\xe4rk\xf6l\xe4</option>\n<option value="karsamaki">K\xe4rs\xe4m\xe4ki</option>\n<option value="kokar">K\xf6kar</option>\n<option value="koylio">K\xf6yli\xf6</option>\n<option value="lahti">Lahti</option>\n<option value="laihia">Laihia</option>\n<option value="laitila">Laitila</option>\n<option value="lammi">Lammi</option>\n<option value="lapinjarvi">Lapinj\xe4rvi</option>\n<option value="lapinlahti">Lapinlahti</option>\n<option value="lappajarvi">Lappaj\xe4rvi</option>\n<option value="lappeenranta">Lappeenranta</option>\n<option value="lappi">Lappi</option>\n<option value="lapua">Lapua</option>\n<option value="laukaa">Laukaa</option>\n<option value="lavia">Lavia</option>\n<option value="lehtimaki">Lehtim\xe4ki</option>\n<option value="leivonmaki">Leivonm\xe4ki</option>\n<option value="lemi">Lemi</option>\n<option value="lemland">Lemland</option>\n<option value="lempaala">Lemp\xe4\xe4l\xe4</option>\n<option value="lemu">Lemu</option>\n<option value="leppavirta">Lepp\xe4virta</option>\n<option value="lestijarvi">Lestij\xe4rvi</option>\n<option value="lieksa">Lieksa</option>\n<option value="lieto">Lieto</option>\n<option value="liljendal">Liljendal</option>\n<option value="liminka">Liminka</option>\n<option value="liperi">Liperi</option>\n<option value="lohja">Lohja</option>\n<option value="lohtaja">Lohtaja</option>\n<option value="loimaa">Loimaa</option>\n<option value="loppi">Loppi</option>\n<option value="loviisa">Loviisa</option>\n<option value="luhanka">Luhanka</option>\n<option value="lumijoki">Lumijoki</option>\n<option value="lumparland">Lumparland</option>\n<option value="luoto">Luoto</option>\n<option value="luumaki">Luum\xe4ki</option>\n<option value="luvia">Luvia</option>\n<option value="maalahti">Maalahti</option>\n<option value="maaninka">Maaninka</option>\n<option value="maarianhamina">Maarianhamina</option>\n<option value="marttila">Marttila</option>\n<option value="masku">Masku</option>\n<option value="mellila">Mellil\xe4</option>\n<option value="merijarvi">Merij\xe4rvi</option>\n<option value="merikarvia">Merikarvia</option>\n<option value="merimasku">Merimasku</option>\n<option value="miehikkala">Miehikk\xe4l\xe4</option>\n<option value="mikkeli">Mikkeli</option>\n<option value="mouhijarvi">Mouhij\xe4rvi</option>\n<option value="muhos">Muhos</option>\n<option value="multia">Multia</option>\n<option value="muonio">Muonio</option>\n<option value="mustasaari">Mustasaari</option>\n<option value="muurame">Muurame</option>\n<option value="muurla">Muurla</option>\n<option value="mynamaki">Myn\xe4m\xe4ki</option>\n<option value="myrskyla">Myrskyl\xe4</option>\n<option value="mantsala">M\xe4nts\xe4l\xe4</option>\n<option value="mantta">M\xe4ntt\xe4</option>\n<option value="mantyharju">M\xe4ntyharju</option>\n<option value="naantali">Naantali</option>\n<option value="nakkila">Nakkila</option>\n<option value="nastola">Nastola</option>\n<option value="nauvo">Nauvo</option>\n<option value="nilsia">Nilsi\xe4</option>\n<option value="nivala">Nivala</option>\n<option value="nokia">Nokia</option>\n<option value="noormarkku">Noormarkku</option>\n<option value="nousiainen">Nousiainen</option>\n<option value="nummi-pusula">Nummi-Pusula</option>\n<option value="nurmes">Nurmes</option>\n<option value="nurmijarvi">Nurmij\xe4rvi</option>\n<option value="nurmo">Nurmo</option>\n<option value="narpio">N\xe4rpi\xf6</option>\n<option value="oravainen">Oravainen</option>\n<option value="orimattila">Orimattila</option>\n<option value="oripaa">Orip\xe4\xe4</option>\n<option value="orivesi">Orivesi</option>\n<option value="oulainen">Oulainen</option>\n<option value="oulu">Oulu</option>\n<option value="oulunsalo">Oulunsalo</option>\n<option value="outokumpu">Outokumpu</option>\n<option value="padasjoki">Padasjoki</option>\n<option value="paimio">Paimio</option>\n<option value="paltamo">Paltamo</option>\n<option value="parainen">Parainen</option>\n<option value="parikkala">Parikkala</option>\n<option value="parkano">Parkano</option>\n<option value="pedersore">Peders\xf6re</option>\n<option value="pelkosenniemi">Pelkosenniemi</option>\n<option value="pello">Pello</option>\n<option value="perho">Perho</option>\n<option value="pernaja">Pernaja</option>\n<option value="pernio">Perni\xf6</option>\n<option value="pertteli">Pertteli</option>\n<option value="pertunmaa">Pertunmaa</option>\n<option value="petajavesi">Pet\xe4j\xe4vesi</option>\n<option value="pieksamaki">Pieks\xe4m\xe4ki</option>\n<option value="pielavesi">Pielavesi</option>\n<option value="pietarsaari">Pietarsaari</option>\n<option value="pihtipudas">Pihtipudas</option>\n<option value="piikkio">Piikki\xf6</option>\n<option value="piippola">Piippola</option>\n<option value="pirkkala">Pirkkala</option>\n<option value="pohja">Pohja</option>\n<option value="polvijarvi">Polvij\xe4rvi</option>\n<option value="pomarkku">Pomarkku</option>\n<option value="pori">Pori</option>\n<option value="pornainen">Pornainen</option>\n<option value="porvoo">Porvoo</option>\n<option value="posio">Posio</option>\n<option value="pudasjarvi">Pudasj\xe4rvi</option>\n<option value="pukkila">Pukkila</option>\n<option value="pulkkila">Pulkkila</option>\n<option value="punkaharju">Punkaharju</option>\n<option value="punkalaidun">Punkalaidun</option>\n<option value="puolanka">Puolanka</option>\n<option value="puumala">Puumala</option>\n<option value="pyhtaa">Pyht\xe4\xe4</option>\n<option value="pyhajoki">Pyh\xe4joki</option>\n<option value="pyhajarvi">Pyh\xe4j\xe4rvi</option>\n<option value="pyhanta">Pyh\xe4nt\xe4</option>\n<option value="pyharanta">Pyh\xe4ranta</option>\n<option value="pyhaselka">Pyh\xe4selk\xe4</option>\n<option value="pylkonmaki">Pylk\xf6nm\xe4ki</option>\n<option value="palkane">P\xe4lk\xe4ne</option>\n<option value="poytya">P\xf6yty\xe4</option>\n<option value="raahe">Raahe</option>\n<option value="raisio">Raisio</option>\n<option value="rantasalmi">Rantasalmi</option>\n<option value="rantsila">Rantsila</option>\n<option value="ranua">Ranua</option>\n<option value="rauma">Rauma</option>\n<option value="rautalampi">Rautalampi</option>\n<option value="rautavaara">Rautavaara</option>\n<option value="rautjarvi">Rautj\xe4rvi</option>\n<option value="reisjarvi">Reisj\xe4rvi</option>\n<option value="renko">Renko</option>\n<option value="riihimaki">Riihim\xe4ki</option>\n<option value="ristiina">Ristiina</option>\n<option value="ristijarvi">Ristij\xe4rvi</option>\n<option value="rovaniemi">Rovaniemi</option>\n<option value="ruokolahti">Ruokolahti</option>\n<option value="ruotsinpyhtaa">Ruotsinpyht\xe4\xe4</option>\n<option value="ruovesi">Ruovesi</option>\n<option value="rusko">Rusko</option>\n<option value="rymattyla">Rym\xe4ttyl\xe4</option>\n<option value="raakkyla">R\xe4\xe4kkyl\xe4</option>\n<option value="saarijarvi">Saarij\xe4rvi</option>\n<option value="salla">Salla</option>\n<option value="salo">Salo</option>\n<option value="saltvik">Saltvik</option>\n<option value="sammatti">Sammatti</option>\n<option value="sauvo">Sauvo</option>\n<option value="savitaipale">Savitaipale</option>\n<option value="savonlinna">Savonlinna</option>\n<option value="savonranta">Savonranta</option>\n<option value="savukoski">Savukoski</option>\n<option value="seinajoki">Sein\xe4joki</option>\n<option value="sievi">Sievi</option>\n<option value="siikainen">Siikainen</option>\n<option value="siikajoki">Siikajoki</option>\n<option value="siilinjarvi">Siilinj\xe4rvi</option>\n<option value="simo">Simo</option>\n<option value="sipoo">Sipoo</option>\n<option value="siuntio">Siuntio</option>\n<option value="sodankyla">Sodankyl\xe4</option>\n<option value="soini">Soini</option>\n<option value="somero">Somero</option>\n<option value="sonkajarvi">Sonkaj\xe4rvi</option>\n<option value="sotkamo">Sotkamo</option>\n<option value="sottunga">Sottunga</option>\n<option value="sulkava">Sulkava</option>\n<option value="sund">Sund</option>\n<option value="suomenniemi">Suomenniemi</option>\n<option value="suomusjarvi">Suomusj\xe4rvi</option>\n<option value="suomussalmi">Suomussalmi</option>\n<option value="suonenjoki">Suonenjoki</option>\n<option value="sysma">Sysm\xe4</option>\n<option value="sakyla">S\xe4kyl\xe4</option>\n<option value="sarkisalo">S\xe4rkisalo</option>\n<option value="taipalsaari">Taipalsaari</option>\n<option value="taivalkoski">Taivalkoski</option>\n<option value="taivassalo">Taivassalo</option>\n<option value="tammela">Tammela</option>\n<option value="tammisaari">Tammisaari</option>\n<option value="tampere">Tampere</option>\n<option value="tarvasjoki">Tarvasjoki</option>\n<option value="tervo">Tervo</option>\n<option value="tervola">Tervola</option>\n<option value="teuva">Teuva</option>\n<option value="tohmajarvi">Tohmaj\xe4rvi</option>\n<option value="toholampi">Toholampi</option>\n<option value="toivakka">Toivakka</option>\n<option value="tornio">Tornio</option>\n<option value="turku" selected="selected">Turku</option>\n<option value="tuulos">Tuulos</option>\n<option value="tuusniemi">Tuusniemi</option>\n<option value="tuusula">Tuusula</option>\n<option value="tyrnava">Tyrn\xe4v\xe4</option>\n<option value="toysa">T\xf6ys\xe4</option>\n<option value="ullava">Ullava</option>\n<option value="ulvila">Ulvila</option>\n<option value="urjala">Urjala</option>\n<option value="utajarvi">Utaj\xe4rvi</option>\n<option value="utsjoki">Utsjoki</option>\n<option value="uurainen">Uurainen</option>\n<option value="uusikaarlepyy">Uusikaarlepyy</option>\n<option value="uusikaupunki">Uusikaupunki</option>\n<option value="vaala">Vaala</option>\n<option value="vaasa">Vaasa</option>\n<option value="vahto">Vahto</option>\n<option value="valkeakoski">Valkeakoski</option>\n<option value="valkeala">Valkeala</option>\n<option value="valtimo">Valtimo</option>\n<option value="vammala">Vammala</option>\n<option value="vampula">Vampula</option>\n<option value="vantaa">Vantaa</option>\n<option value="varkaus">Varkaus</option>\n<option value="varpaisjarvi">Varpaisj\xe4rvi</option>\n<option value="vehmaa">Vehmaa</option>\n<option value="velkua">Velkua</option>\n<option value="vesanto">Vesanto</option>\n<option value="vesilahti">Vesilahti</option>\n<option value="veteli">Veteli</option>\n<option value="vierema">Vierem\xe4</option>\n<option value="vihanti">Vihanti</option>\n<option value="vihti">Vihti</option>\n<option value="viitasaari">Viitasaari</option>\n<option value="vilppula">Vilppula</option>\n<option value="vimpeli">Vimpeli</option>\n<option value="virolahti">Virolahti</option>\n<option value="virrat">Virrat</option>\n<option value="vardo">V\xe5rd\xf6</option>\n<option value="vahakyro">V\xe4h\xe4kyr\xf6</option>\n<option value="vastanfjard">V\xe4stanfj\xe4rd</option>\n<option value="voyri-maksamaa">V\xf6yri-Maksamaa</option>\n<option value="yliharma">Ylih\xe4rm\xe4</option>\n<option value="yli-ii">Yli-Ii</option>\n<option value="ylikiiminki">Ylikiiminki</option>\n<option value="ylistaro">Ylistaro</option>\n<option value="ylitornio">Ylitornio</option>\n<option value="ylivieska">Ylivieska</option>\n<option value="ylamaa">Yl\xe4maa</option>\n<option value="ylane">Yl\xe4ne</option>\n<option value="ylojarvi">Yl\xf6j\xe4rvi</option>\n<option value="ypaja">Yp\xe4j\xe4</option>\n<option value="aetsa">\xc4ets\xe4</option>\n<option value="ahtari">\xc4ht\xe4ri</option>\n<option value="aanekoski">\xc4\xe4nekoski</option>\n</select>'

# FISocialSecurityNumber
##############################################################

>>> from django.contrib.localflavor.fi.forms import FISocialSecurityNumber
>>> f = FISocialSecurityNumber()
>>> f.clean('010101-0101')
u'010101-0101'
>>> f.clean('010101+0101')
u'010101+0101'
>>> f.clean('010101A0101')
u'010101A0101'
>>> f.clean('101010-0102')
Traceback (most recent call last):
...
ValidationError: [u'Enter a valid Finnish social security number.']
>>> f.clean('10a010-0101')
Traceback (most recent call last):
...
ValidationError: [u'Enter a valid Finnish social security number.']
>>> f.clean('101010-0\xe401')
Traceback (most recent call last):
...
ValidationError: [u'Enter a valid Finnish social security number.']
>>> f.clean('101010b0101')
Traceback (most recent call last):
...
ValidationError: [u'Enter a valid Finnish social security number.']
>>> f.clean('')
Traceback (most recent call last):
...
ValidationError: [u'This field is required.']

>>> f.clean(None)
Traceback (most recent call last):
...
ValidationError: [u'This field is required.']
>>> f = FISocialSecurityNumber(required=False)
>>> f.clean('010101-0101')
u'010101-0101'
>>> f.clean(None)
u''
>>> f.clean('')
u''

# BRZipCodeField ############################################################
>>> from django.contrib.localflavor.br.forms import BRZipCodeField
>>> f = BRZipCodeField()
>>> f.clean('12345-123')
u'12345-123'
>>> f.clean('12345_123')
Traceback (most recent call last):
...
ValidationError: [u'Enter a zip code in the format XXXXX-XXX.']
>>> f.clean('1234-123')
Traceback (most recent call last):
...
ValidationError: [u'Enter a zip code in the format XXXXX-XXX.']
>>> f.clean('abcde-abc')
Traceback (most recent call last):
...
ValidationError: [u'Enter a zip code in the format XXXXX-XXX.']
>>> f.clean('12345-')
Traceback (most recent call last):
...
ValidationError: [u'Enter a zip code in the format XXXXX-XXX.']
>>> f.clean('-123')
Traceback (most recent call last):
...
ValidationError: [u'Enter a zip code in the format XXXXX-XXX.']
>>> f.clean('')
Traceback (most recent call last):
...
ValidationError: [u'This field is required.']
>>> f.clean(None)
Traceback (most recent call last):
...
ValidationError: [u'This field is required.']

>>> f = BRZipCodeField(required=False)
>>> f.clean(None)
u''
>>> f.clean('')
u''
>>> f.clean('-123')
Traceback (most recent call last):
...
ValidationError: [u'Enter a zip code in the format XXXXX-XXX.']
>>> f.clean('12345-')
Traceback (most recent call last):
...
ValidationError: [u'Enter a zip code in the format XXXXX-XXX.']
>>> f.clean('abcde-abc')
Traceback (most recent call last):
...
ValidationError: [u'Enter a zip code in the format XXXXX-XXX.']
>>> f.clean('1234-123')
Traceback (most recent call last):
...
ValidationError: [u'Enter a zip code in the format XXXXX-XXX.']
>>> f.clean('12345_123')
Traceback (most recent call last):
...
ValidationError: [u'Enter a zip code in the format XXXXX-XXX.']
>>> f.clean('12345-123')
u'12345-123'

# BRPhoneNumberField #########################################################

>>> from django.contrib.localflavor.br.forms import BRPhoneNumberField
>>> f = BRPhoneNumberField()
>>> f.clean('41-3562-3464')
u'41-3562-3464'
>>> f.clean('4135623464')
u'41-3562-3464'
>>> f.clean('41 3562-3464')
u'41-3562-3464'
>>> f.clean('41 3562 3464')
u'41-3562-3464'
>>> f.clean('(41) 3562 3464')
u'41-3562-3464'
>>> f.clean('41.3562.3464')
u'41-3562-3464'
>>> f.clean('41.3562-3464')
u'41-3562-3464'
>>> f.clean(' (41) 3562.3464')
u'41-3562-3464'
>>> f.clean(None)
Traceback (most recent call last):
...
ValidationError: [u'This field is required.']
>>> f.clean('')
Traceback (most recent call last):
...
ValidationError: [u'This field is required.']

>>> f = BRPhoneNumberField(required=False)
>>> f.clean('')
u''
>>> f.clean(None)
u''
>>> f.clean(' (41) 3562.3464')
u'41-3562-3464'
>>> f.clean('41.3562-3464')
u'41-3562-3464'
>>> f.clean('(41) 3562 3464')
u'41-3562-3464'
>>> f.clean('4135623464')
u'41-3562-3464'
>>> f.clean('41 3562-3464')
u'41-3562-3464'

# BRStateSelect ##############################################################

>>> from django.contrib.localflavor.br.forms import BRStateSelect
>>> w = BRStateSelect()
>>> w.render('states', 'PR')
u'<select name="states">\n<option value="AC">Acre</option>\n<option value="AL">Alagoas</option>\n<option value="AP">Amap\xe1</option>\n<option value="AM">Amazonas</option>\n<option value="BA">Bahia</option>\n<option value="CE">Cear\xe1</option>\n<option value="DF">Distrito Federal</option>\n<option value="ES">Esp\xedrito Santo</option>\n<option value="GO">Goi\xe1s</option>\n<option value="MA">Maranh\xe3o</option>\n<option value="MT">Mato Grosso</option>\n<option value="MS">Mato Grosso do Sul</option>\n<option value="MG">Minas Gerais</option>\n<option value="PA">Par\xe1</option>\n<option value="PB">Para\xedba</option>\n<option value="PR" selected="selected">Paran\xe1</option>\n<option value="PE">Pernambuco</option>\n<option value="PI">Piau\xed</option>\n<option value="RJ">Rio de Janeiro</option>\n<option value="RN">Rio Grande do Norte</option>\n<option value="RS">Rio Grande do Sul</option>\n<option value="RO">Rond\xf4nia</option>\n<option value="RR">Roraima</option>\n<option value="SC">Santa Catarina</option>\n<option value="SP">S\xe3o Paulo</option>\n<option value="SE">Sergipe</option>\n<option value="TO">Tocantins</option>\n</select>'

# DEZipCodeField ##############################################################

>>> from django.contrib.localflavor.de.forms import DEZipCodeField
>>> f = DEZipCodeField()
>>> f.clean('99423')
u'99423'
>>> f.clean(' 99423')
Traceback (most recent call last):
...
ValidationError: [u'Enter a zip code in the format XXXXX.']

# DEStateSelect #############################################################

>>> from django.contrib.localflavor.de.forms import DEStateSelect
>>> w = DEStateSelect()
>>> w.render('states', 'TH')
u'<select name="states">\n<option value="BW">Baden-Wuerttemberg</option>\n<option value="BY">Bavaria</option>\n<option value="BE">Berlin</option>\n<option value="BB">Brandenburg</option>\n<option value="HB">Bremen</option>\n<option value="HH">Hamburg</option>\n<option value="HE">Hessen</option>\n<option value="MV">Mecklenburg-Western Pomerania</option>\n<option value="NI">Lower Saxony</option>\n<option value="NW">North Rhine-Westphalia</option>\n<option value="RP">Rhineland-Palatinate</option>\n<option value="SL">Saarland</option>\n<option value="SN">Saxony</option>\n<option value="ST">Saxony-Anhalt</option>\n<option value="SH">Schleswig-Holstein</option>\n<option value="TH" selected="selected">Thuringia</option>\n</select>'

# DEIdentityCardNumberField #################################################

>>> from django.contrib.localflavor.de.forms import DEIdentityCardNumberField
>>> f = DEIdentityCardNumberField()
>>> f.clean('7549313035D-6004103-0903042-0')
u'7549313035D-6004103-0903042-0'
>>> f.clean('9786324830D 6104243 0910271 2')
u'9786324830D-6104243-0910271-2'
>>> f.clean('0434657485D-6407276-0508137-9')
Traceback (most recent call last):
...
ValidationError: [u'Enter a valid German identity card number in XXXXXXXXXXX-XXXXXXX-XXXXXXX-X format.']

## AUPostCodeField ##########################################################

A field that accepts a four digit Australian post code.

>>> from django.contrib.localflavor.au.forms import AUPostCodeField
>>> f = AUPostCodeField()
>>> f.clean('1234')
u'1234'
>>> f.clean('2000')
u'2000'
>>> f.clean('abcd')
Traceback (most recent call last):
...
ValidationError: [u'Enter a 4 digit post code.']
>>> f.clean('20001')
Traceback (most recent call last):
...
ValidationError: [u'Enter a 4 digit post code.']
>>> f.clean(None)
Traceback (most recent call last):
...
ValidationError: [u'This field is required.']
>>> f.clean('')
Traceback (most recent call last):
...
ValidationError: [u'This field is required.']

>>> f = AUPostCodeField(required=False)
>>> f.clean('1234')
u'1234'
>>> f.clean('2000')
u'2000'
>>> f.clean('abcd')
Traceback (most recent call last):
...
ValidationError: [u'Enter a 4 digit post code.']
>>> f.clean('20001')
Traceback (most recent call last):
...
ValidationError: [u'Enter a 4 digit post code.']
>>> f.clean(None)
u''
>>> f.clean('')
u''

## AUPhoneNumberField ########################################################

A field that accepts a 10 digit Australian phone number.
llows spaces and parentheses around area code.

>>> from django.contrib.localflavor.au.forms import AUPhoneNumberField
>>> f = AUPhoneNumberField()
>>> f.clean('1234567890')
u'1234567890'
>>> f.clean('0213456789')
u'0213456789'
>>> f.clean('02 13 45 67 89')
u'0213456789'
>>> f.clean('(02) 1345 6789')
u'0213456789'
>>> f.clean('(02) 1345-6789')
u'0213456789'
>>> f.clean('(02)1345-6789')
u'0213456789'
>>> f.clean('0408 123 456')
u'0408123456'
>>> f.clean('123')
Traceback (most recent call last):
...
ValidationError: [u'Phone numbers must contain 10 digits.']
>>> f.clean('1800DJANGO')
Traceback (most recent call last):
...
ValidationError: [u'Phone numbers must contain 10 digits.']
>>> f.clean(None)
Traceback (most recent call last):
...
ValidationError: [u'This field is required.']
>>> f.clean('')
Traceback (most recent call last):
...
ValidationError: [u'This field is required.']

>>> f = AUPhoneNumberField(required=False)
>>> f.clean('1234567890')
u'1234567890'
>>> f.clean('0213456789')
u'0213456789'
>>> f.clean('02 13 45 67 89')
u'0213456789'
>>> f.clean('(02) 1345 6789')
u'0213456789'
>>> f.clean('(02) 1345-6789')
u'0213456789'
>>> f.clean('(02)1345-6789')
u'0213456789'
>>> f.clean('0408 123 456')
u'0408123456'
>>> f.clean('123')
Traceback (most recent call last):
...
ValidationError: [u'Phone numbers must contain 10 digits.']
>>> f.clean('1800DJANGO')
Traceback (most recent call last):
...
ValidationError: [u'Phone numbers must contain 10 digits.']
>>> f.clean(None)
u''
>>> f.clean('')
u''

## AUStateSelect #############################################################

AUStateSelect is a Select widget that uses a list of Australian
states/territories as its choices.

>>> from django.contrib.localflavor.au.forms import AUStateSelect
>>> f = AUStateSelect()
>>> print f.render('state', 'NSW')
<select name="state">
<option value="ACT">Australian Capital Territory</option>
<option value="NSW" selected="selected">New South Wales</option>
<option value="NT">Northern Territory</option>
<option value="QLD">Queensland</option>
<option value="SA">South Australia</option>
<option value="TAS">Tasmania</option>
<option value="VIC">Victoria</option>
<option value="WA">Western Australia</option>
</select>

## ISIdNumberField #############################################################

>>> from django.contrib.localflavor.is_.forms import *
>>> f = ISIdNumberField()
>>> f.clean('2308803449')
u'230880-3449'
>>> f.clean('230880-3449')
u'230880-3449'
>>> f.clean('230880 3449')
u'230880-3449'
>>> f.clean('230880343')
Traceback (most recent call last):
...
ValidationError: [u'Ensure this value has at least 10 characters.']
>>> f.clean('230880343234')
Traceback (most recent call last):
...
ValidationError: [u'Ensure this value has at most 11 characters.']
>>> f.clean('abcdefghijk')
Traceback (most recent call last):
...
ValidationError: [u'Enter a valid Icelandic identification number. The format is XXXXXX-XXXX.']
>>> f.clean('')
Traceback (most recent call last):
...
ValidationError: [u'This field is required.']
>>> f.clean(None)
Traceback (most recent call last):
...
ValidationError: [u'This field is required.']
>>> f.clean('2308803439')
Traceback (most recent call last):
...
ValidationError: [u'The Icelandic identification number is not valid.']
>>> f.clean('2308803440')
u'230880-3440'
>>> f = ISIdNumberField(required=False)
>>> f.clean(None)
u''
>>> f.clean('')
u''

## ISPhoneNumberField #############################################################

>>> from django.contrib.localflavor.is_.forms import *
>>> f = ISPhoneNumberField()
>>> f.clean('1234567')
u'1234567'
>>> f.clean('123 4567')
u'1234567'
>>> f.clean('123-4567')
u'1234567'
>>> f.clean('123-456')
Traceback (most recent call last):
...
ValidationError: [u'Enter a valid value.']
>>> f.clean('123456')
Traceback (most recent call last):
...
ValidationError: [u'Ensure this value has at least 7 characters.']
>>> f.clean('123456555')
Traceback (most recent call last):
...
ValidationError: [u'Ensure this value has at most 8 characters.']
>>> f.clean('abcdefg')
Traceback (most recent call last):
ValidationError: [u'Enter a valid value.']
>>> f.clean(' 1234567 ')
Traceback (most recent call last):
...
ValidationError: [u'Ensure this value has at most 8 characters.']
>>> f.clean(' 12367  ')
Traceback (most recent call last):
...
ValidationError: [u'Enter a valid value.']

>>> f.clean('')
Traceback (most recent call last):
...
ValidationError: [u'This field is required.']
>>> f.clean(None)
Traceback (most recent call last):
...
ValidationError: [u'This field is required.']
>>> f = ISPhoneNumberField(required=False)
>>> f.clean(None)
u''
>>> f.clean('')
u''

## ISPostalCodeSelect #############################################################

>>> from django.contrib.localflavor.is_.forms import *
>>> f = ISPostalCodeSelect()

>>> f.render('foo', 'bar')
u'<select name="foo">\n<option value="101">101 Reykjav\xedk</option>\n<option value="103">103 Reykjav\xedk</option>\n<option value="104">104 Reykjav\xedk</option>\n<option value="105">105 Reykjav\xedk</option>\n<option value="107">107 Reykjav\xedk</option>\n<option value="108">108 Reykjav\xedk</option>\n<option value="109">109 Reykjav\xedk</option>\n<option value="110">110 Reykjav\xedk</option>\n<option value="111">111 Reykjav\xedk</option>\n<option value="112">112 Reykjav\xedk</option>\n<option value="113">113 Reykjav\xedk</option>\n<option value="116">116 Kjalarnes</option>\n<option value="121">121 Reykjav\xedk</option>\n<option value="123">123 Reykjav\xedk</option>\n<option value="124">124 Reykjav\xedk</option>\n<option value="125">125 Reykjav\xedk</option>\n<option value="127">127 Reykjav\xedk</option>\n<option value="128">128 Reykjav\xedk</option>\n<option value="129">129 Reykjav\xedk</option>\n<option value="130">130 Reykjav\xedk</option>\n<option value="132">132 Reykjav\xedk</option>\n<option value="150">150 Reykjav\xedk</option>\n<option value="155">155 Reykjav\xedk</option>\n<option value="170">170 Seltjarnarnes</option>\n<option value="172">172 Seltjarnarnes</option>\n<option value="190">190 Vogar</option>\n<option value="200">200 K\xf3pavogur</option>\n<option value="201">201 K\xf3pavogur</option>\n<option value="202">202 K\xf3pavogur</option>\n<option value="203">203 K\xf3pavogur</option>\n<option value="210">210 Gar\xf0ab\xe6r</option>\n<option value="212">212 Gar\xf0ab\xe6r</option>\n<option value="220">220 Hafnarfj\xf6r\xf0ur</option>\n<option value="221">221 Hafnarfj\xf6r\xf0ur</option>\n<option value="222">222 Hafnarfj\xf6r\xf0ur</option>\n<option value="225">225 \xc1lftanes</option>\n<option value="230">230 Reykjanesb\xe6r</option>\n<option value="232">232 Reykjanesb\xe6r</option>\n<option value="233">233 Reykjanesb\xe6r</option>\n<option value="235">235 Keflav\xedkurflugv\xf6llur</option>\n<option value="240">240 Grindav\xedk</option>\n<option value="245">245 Sandger\xf0i</option>\n<option value="250">250 Gar\xf0ur</option>\n<option value="260">260 Reykjanesb\xe6r</option>\n<option value="270">270 Mosfellsb\xe6r</option>\n<option value="300">300 Akranes</option>\n<option value="301">301 Akranes</option>\n<option value="302">302 Akranes</option>\n<option value="310">310 Borgarnes</option>\n<option value="311">311 Borgarnes</option>\n<option value="320">320 Reykholt \xed Borgarfir\xf0i</option>\n<option value="340">340 Stykkish\xf3lmur</option>\n<option value="345">345 Flatey \xe1 Brei\xf0afir\xf0i</option>\n<option value="350">350 Grundarfj\xf6r\xf0ur</option>\n<option value="355">355 \xd3lafsv\xedk</option>\n<option value="356">356 Sn\xe6fellsb\xe6r</option>\n<option value="360">360 Hellissandur</option>\n<option value="370">370 B\xfa\xf0ardalur</option>\n<option value="371">371 B\xfa\xf0ardalur</option>\n<option value="380">380 Reykh\xf3lahreppur</option>\n<option value="400">400 \xcdsafj\xf6r\xf0ur</option>\n<option value="401">401 \xcdsafj\xf6r\xf0ur</option>\n<option value="410">410 Hn\xedfsdalur</option>\n<option value="415">415 Bolungarv\xedk</option>\n<option value="420">420 S\xfa\xf0av\xedk</option>\n<option value="425">425 Flateyri</option>\n<option value="430">430 Su\xf0ureyri</option>\n<option value="450">450 Patreksfj\xf6r\xf0ur</option>\n<option value="451">451 Patreksfj\xf6r\xf0ur</option>\n<option value="460">460 T\xe1lknafj\xf6r\xf0ur</option>\n<option value="465">465 B\xedldudalur</option>\n<option value="470">470 \xdeingeyri</option>\n<option value="471">471 \xdeingeyri</option>\n<option value="500">500 Sta\xf0ur</option>\n<option value="510">510 H\xf3lmav\xedk</option>\n<option value="512">512 H\xf3lmav\xedk</option>\n<option value="520">520 Drangsnes</option>\n<option value="522">522 Kj\xf6rvogur</option>\n<option value="523">523 B\xe6r</option>\n<option value="524">524 Nor\xf0urfj\xf6r\xf0ur</option>\n<option value="530">530 Hvammstangi</option>\n<option value="531">531 Hvammstangi</option>\n<option value="540">540 Bl\xf6ndu\xf3s</option>\n<option value="541">541 Bl\xf6ndu\xf3s</option>\n<option value="545">545 Skagastr\xf6nd</option>\n<option value="550">550 Sau\xf0\xe1rkr\xf3kur</option>\n<option value="551">551 Sau\xf0\xe1rkr\xf3kur</option>\n<option value="560">560 Varmahl\xed\xf0</option>\n<option value="565">565 Hofs\xf3s</option>\n<option value="566">566 Hofs\xf3s</option>\n<option value="570">570 Flj\xf3t</option>\n<option value="580">580 Siglufj\xf6r\xf0ur</option>\n<option value="600">600 Akureyri</option>\n<option value="601">601 Akureyri</option>\n<option value="602">602 Akureyri</option>\n<option value="603">603 Akureyri</option>\n<option value="610">610 Greniv\xedk</option>\n<option value="611">611 Gr\xedmsey</option>\n<option value="620">620 Dalv\xedk</option>\n<option value="621">621 Dalv\xedk</option>\n<option value="625">625 \xd3lafsfj\xf6r\xf0ur</option>\n<option value="630">630 Hr\xedsey</option>\n<option value="640">640 H\xfasav\xedk</option>\n<option value="641">641 H\xfasav\xedk</option>\n<option value="645">645 Fossh\xf3ll</option>\n<option value="650">650 Laugar</option>\n<option value="660">660 M\xfdvatn</option>\n<option value="670">670 K\xf3pasker</option>\n<option value="671">671 K\xf3pasker</option>\n<option value="675">675 Raufarh\xf6fn</option>\n<option value="680">680 \xde\xf3rsh\xf6fn</option>\n<option value="681">681 \xde\xf3rsh\xf6fn</option>\n<option value="685">685 Bakkafj\xf6r\xf0ur</option>\n<option value="690">690 Vopnafj\xf6r\xf0ur</option>\n<option value="700">700 Egilssta\xf0ir</option>\n<option value="701">701 Egilssta\xf0ir</option>\n<option value="710">710 Sey\xf0isfj\xf6r\xf0ur</option>\n<option value="715">715 Mj\xf3ifj\xf6r\xf0ur</option>\n<option value="720">720 Borgarfj\xf6r\xf0ur eystri</option>\n<option value="730">730 Rey\xf0arfj\xf6r\xf0ur</option>\n<option value="735">735 Eskifj\xf6r\xf0ur</option>\n<option value="740">740 Neskaupsta\xf0ur</option>\n<option value="750">750 F\xe1skr\xfa\xf0sfj\xf6r\xf0ur</option>\n<option value="755">755 St\xf6\xf0varfj\xf6r\xf0ur</option>\n<option value="760">760 Brei\xf0dalsv\xedk</option>\n<option value="765">765 Dj\xfapivogur</option>\n<option value="780">780 H\xf6fn \xed Hornafir\xf0i</option>\n<option value="781">781 H\xf6fn \xed Hornafir\xf0i</option>\n<option value="785">785 \xd6r\xe6fi</option>\n<option value="800">800 Selfoss</option>\n<option value="801">801 Selfoss</option>\n<option value="802">802 Selfoss</option>\n<option value="810">810 Hverager\xf0i</option>\n<option value="815">815 \xdeorl\xe1ksh\xf6fn</option>\n<option value="820">820 Eyrarbakki</option>\n<option value="825">825 Stokkseyri</option>\n<option value="840">840 Laugarvatn</option>\n<option value="845">845 Fl\xfa\xf0ir</option>\n<option value="850">850 Hella</option>\n<option value="851">851 Hella</option>\n<option value="860">860 Hvolsv\xf6llur</option>\n<option value="861">861 Hvolsv\xf6llur</option>\n<option value="870">870 V\xedk</option>\n<option value="871">871 V\xedk</option>\n<option value="880">880 Kirkjub\xe6jarklaustur</option>\n<option value="900">900 Vestmannaeyjar</option>\n<option value="902">902 Vestmannaeyjar</option>\n</select>'

## CLRutField #############################################################

CLRutField is a Field that checks the validity of the Chilean
personal identification number (RUT). It has two modes relaxed (default) and
strict.

>>> from django.contrib.localflavor.cl.forms import CLRutField
>>> rut = CLRutField()

>>> rut.clean('11-6')
'11-6'
>>> rut.clean('116')
'11-6'

# valid format, bad verifier.
>>> rut.clean('11.111.111-0')
Traceback (most recent call last):
...
ValidationError: [u'The Chilean RUT is not valid.']
>>> rut.clean('111')
Traceback (most recent call last):
...
ValidationError: [u'The Chilean RUT is not valid.']

>>> rut.clean('767484100')
'76.748.410-0'
>>> rut.clean('78.412.790-7')
'78.412.790-7'
>>> rut.clean('8.334.6043')
'8.334.604-3'
>>> rut.clean('76793310-K')
'76.793.310-K'

Strict RUT usage (does not allow imposible values)
>>> rut = CLRutField(strict=True)

>>> rut.clean('11-6')
Traceback (most recent call last):
...
ValidationError: [u'Enter valid a Chilean RUT. The format is XX.XXX.XXX-X.']

# valid format, bad verifier.
>>> rut.clean('11.111.111-0')
Traceback (most recent call last):
...
ValidationError: [u'The Chilean RUT is not valid.']

# Correct input, invalid format.
>>> rut.clean('767484100')
Traceback (most recent call last):
...
ValidationError: [u'Enter valid a Chilean RUT. The format is XX.XXX.XXX-X.']
>>> rut.clean('78.412.790-7')
'78.412.790-7'
>>> rut.clean('8.334.6043')
Traceback (most recent call last):
...
ValidationError: [u'Enter valid a Chilean RUT. The format is XX.XXX.XXX-X.']
>>> rut.clean('76793310-K')
Traceback (most recent call last):
...
ValidationError: [u'Enter valid a Chilean RUT. The format is XX.XXX.XXX-X.']

"""
