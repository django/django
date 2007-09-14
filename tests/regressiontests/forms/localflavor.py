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

# BRCNPJField ############################################################

>>> from django.contrib.localflavor.br.forms import BRCNPJField
>>> f = BRCNPJField(required=True)
>>> f.clean('')
Traceback (most recent call last):
...
ValidationError: [u'This field is required.']
>>> f.clean('12-345-678/9012-10')
Traceback (most recent call last):
...
ValidationError: [u'Invalid CNPJ number.']
>>> f.clean('12.345.678/9012-10')
Traceback (most recent call last):
...
ValidationError: [u'Invalid CNPJ number.']
>>> f.clean('12345678/9012-10')
Traceback (most recent call last):
...
ValidationError: [u'Invalid CNPJ number.']
>>> f.clean('64.132.916/0001-88')
'64.132.916/0001-88'
>>> f.clean('64-132-916/0001-88')
'64-132-916/0001-88'
>>> f.clean('64132916/0001-88')
'64132916/0001-88'
>>> f.clean('64.132.916/0001-XX')
Traceback (most recent call last):
...
ValidationError: [u'This field requires only numbers.']
>>> f = BRCNPJField(required=False)
>>> f.clean('')
u''

# BRCPFField #################################################################

>>> from django.contrib.localflavor.br.forms import BRCPFField
>>> f = BRCPFField()
>>> f.clean('')
Traceback (most recent call last):
...
ValidationError: [u'This field is required.']
>>> f.clean(None)
Traceback (most recent call last):
...
ValidationError: [u'This field is required.']
>>> f.clean('489.294.654-54')
Traceback (most recent call last):
...
ValidationError: [u'Invalid CPF number.']
>>> f.clean('295.669.575-98')
Traceback (most recent call last):
...
ValidationError: [u'Invalid CPF number.']
>>> f.clean('539.315.127-22')
Traceback (most recent call last):
...
ValidationError: [u'Invalid CPF number.']
>>> f.clean('663.256.017-26')
u'663.256.017-26'
>>> f.clean('66325601726')
u'66325601726'
>>> f.clean('375.788.573-20')
u'375.788.573-20'
>>> f.clean('84828509895')
u'84828509895'
>>> f.clean('375.788.573-XX')
Traceback (most recent call last):
...
ValidationError: [u'This field requires only numbers.']
>>> f.clean('375.788.573-000')
Traceback (most recent call last):
...
ValidationError: [u'Ensure this value has at most 14 characters (it has 15).']
>>> f.clean('123.456.78')
Traceback (most recent call last):
...
ValidationError: [u'Ensure this value has at least 11 characters (it has 10).']
>>> f.clean('123456789555')
Traceback (most recent call last):
...
ValidationError: [u'This field requires at most 11 digits or 14 characters.']
>>> f = BRCPFField(required=False)
>>> f.clean('')
u''
>>> f.clean(None)
u''

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

# BRStateChoiceField #########################################################
>>> from django.contrib.localflavor.br.forms import BRStateChoiceField
>>> f = BRStateChoiceField()
>>> ', '.join([f.clean(s) for s, _ in f.widget.choices])
u'AC, AL, AP, AM, BA, CE, DF, ES, GO, MA, MT, MS, MG, PA, PB, PR, PE, PI, RJ, RN, RS, RO, RR, SC, SP, SE, TO'
>>> f.clean('')
Traceback (most recent call last):
...
ValidationError: [u'This field is required.']
>>> f.clean('pr')
Traceback (most recent call last):
...
ValidationError: [u'Select a valid brazilian state. That state is not one of the available states.']

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

# CHZipCodeField ############################################################

>>> from django.contrib.localflavor.ch.forms import CHZipCodeField
>>> f = CHZipCodeField()
>>> f.clean('800x')
Traceback (most recent call last):
...
ValidationError: [u'Enter a zip code in the format XXXX.']
>>> f.clean('80 00')
Traceback (most recent call last):
...
ValidationError: [u'Enter a zip code in the format XXXX.']
>>> f.clean('8000')
u'8000'

# CHPhoneNumberField ########################################################

>>> from django.contrib.localflavor.ch.forms import CHPhoneNumberField
>>> f = CHPhoneNumberField()
>>> f.clean('01234567890')
Traceback (most recent call last):
...
ValidationError: [u'Phone numbers must be in 0XX XXX XX XX format.']
>>> f.clean('1234567890')
Traceback (most recent call last):
...
ValidationError: [u'Phone numbers must be in 0XX XXX XX XX format.']
>>> f.clean('0123456789')
u'012 345 67 89'

# CHIdentityCardNumberField #################################################

>>> from django.contrib.localflavor.ch.forms import CHIdentityCardNumberField
>>> f = CHIdentityCardNumberField()
>>> f.clean('C1234567<0')
u'C1234567<0'
>>> f.clean('C1234567<1')
Traceback (most recent call last):
...
ValidationError: [u'Enter a valid Swiss identity or passport card number in X1234567<0 or 1234567890 format.']
>>> f.clean('2123456700')
u'2123456700'
>>> f.clean('2123456701')
Traceback (most recent call last):
...
ValidationError: [u'Enter a valid Swiss identity or passport card number in X1234567<0 or 1234567890 format.']

# CHStateSelect #############################################################

>>> from django.contrib.localflavor.ch.forms import CHStateSelect
>>> w = CHStateSelect()
>>> w.render('state', 'AG')
u'<select name="state">\n<option value="AG" selected="selected">Aargau</option>\n<option value="AI">Appenzell Innerrhoden</option>\n<option value="AR">Appenzell Ausserrhoden</option>\n<option value="BS">Basel-Stadt</option>\n<option value="BL">Basel-Land</option>\n<option value="BE">Berne</option>\n<option value="FR">Fribourg</option>\n<option value="GE">Geneva</option>\n<option value="GL">Glarus</option>\n<option value="GR">Graubuenden</option>\n<option value="JU">Jura</option>\n<option value="LU">Lucerne</option>\n<option value="NE">Neuchatel</option>\n<option value="NW">Nidwalden</option>\n<option value="OW">Obwalden</option>\n<option value="SH">Schaffhausen</option>\n<option value="SZ">Schwyz</option>\n<option value="SO">Solothurn</option>\n<option value="SG">St. Gallen</option>\n<option value="TG">Thurgau</option>\n<option value="TI">Ticino</option>\n<option value="UR">Uri</option>\n<option value="VS">Valais</option>\n<option value="VD">Vaud</option>\n<option value="ZG">Zug</option>\n<option value="ZH">Zurich</option>\n</select>'

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
ValidationError: [u'Ensure this value has at least 10 characters (it has 9).']
>>> f.clean('230880343234')
Traceback (most recent call last):
...
ValidationError: [u'Ensure this value has at most 11 characters (it has 12).']
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
ValidationError: [u'Ensure this value has at least 7 characters (it has 6).']
>>> f.clean('123456555')
Traceback (most recent call last):
...
ValidationError: [u'Ensure this value has at most 8 characters (it has 9).']
>>> f.clean('abcdefg')
Traceback (most recent call last):
ValidationError: [u'Enter a valid value.']
>>> f.clean(' 1234567 ')
Traceback (most recent call last):
...
ValidationError: [u'Ensure this value has at most 8 characters (it has 9).']
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
u'11-6'
>>> rut.clean('116')
u'11-6'

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
u'76.748.410-0'
>>> rut.clean('78.412.790-7')
u'78.412.790-7'
>>> rut.clean('8.334.6043')
u'8.334.604-3'
>>> rut.clean('76793310-K')
u'76.793.310-K'

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
u'78.412.790-7'
>>> rut.clean('8.334.6043')
Traceback (most recent call last):
...
ValidationError: [u'Enter valid a Chilean RUT. The format is XX.XXX.XXX-X.']
>>> rut.clean('76793310-K')
Traceback (most recent call last):
...
ValidationError: [u'Enter valid a Chilean RUT. The format is XX.XXX.XXX-X.']

## CLRegionSelect #########################################################
>>> from django.contrib.localflavor.cl.forms import CLRegionSelect
>>> f = CLRegionSelect()

>>> f.render('foo', 'bar')
u'<select name="foo">\n<option value="RM">Regi\xf3n Metropolitana de Santiago</option>\n<option value="I">Regi\xf3n de Tarapac\xe1</option>\n<option value="II">Regi\xf3n de Antofagasta</option>\n<option value="III">Regi\xf3n de Atacama</option>\n<option value="IV">Regi\xf3n de Coquimbo</option>\n<option value="V">Regi\xf3n de Valpara\xedso</option>\n<option value="VI">Regi\xf3n del Libertador Bernardo O&#39;Higgins</option>\n<option value="VII">Regi\xf3n del Maule</option>\n<option value="VIII">Regi\xf3n del B\xedo B\xedo</option>\n<option value="IX">Regi\xf3n de la Araucan\xeda</option>\n<option value="X">Regi\xf3n de los Lagos</option>\n<option value="XI">Regi\xf3n de Ays\xe9n del General Carlos Ib\xe1\xf1ez del Campo</option>\n<option value="XII">Regi\xf3n de Magallanes y la Ant\xe1rtica Chilena</option>\n<option value="XIV">Regi\xf3n de Los R\xedos</option>\n<option value="XV">Regi\xf3n de Arica-Parinacota</option>\n</select>'

# SKPostalCodeField #########################################################

>>> from django.contrib.localflavor.sk.forms import SKPostalCodeField
>>> f = SKPostalCodeField()
>>> f.clean('84545x')
Traceback (most recent call last):
...
ValidationError: [u'Enter a postal code in the format XXXXX or XXX XX.']
>>> f.clean('91909')
u'91909'
>>> f.clean('917 01')
u'91701'

# SKRegionSelect ############################################################

>>> from django.contrib.localflavor.sk.forms import SKRegionSelect
>>> w = SKRegionSelect()
>>> w.render('regions', 'TT')
u'<select name="regions">\n<option value="BB">Banska Bystrica region</option>\n<option value="BA">Bratislava region</option>\n<option value="KE">Kosice region</option>\n<option value="NR">Nitra region</option>\n<option value="PO">Presov region</option>\n<option value="TN">Trencin region</option>\n<option value="TT" selected="selected">Trnava region</option>\n<option value="ZA">Zilina region</option>\n</select>'

# SKDistrictSelect ##########################################################

>>> from django.contrib.localflavor.sk.forms import SKDistrictSelect
>>> w = SKDistrictSelect()
>>> w.render('Districts', 'RK')
u'<select name="Districts">\n<option value="BB">Banska Bystrica</option>\n<option value="BS">Banska Stiavnica</option>\n<option value="BJ">Bardejov</option>\n<option value="BN">Banovce nad Bebravou</option>\n<option value="BR">Brezno</option>\n<option value="BA1">Bratislava I</option>\n<option value="BA2">Bratislava II</option>\n<option value="BA3">Bratislava III</option>\n<option value="BA4">Bratislava IV</option>\n<option value="BA5">Bratislava V</option>\n<option value="BY">Bytca</option>\n<option value="CA">Cadca</option>\n<option value="DT">Detva</option>\n<option value="DK">Dolny Kubin</option>\n<option value="DS">Dunajska Streda</option>\n<option value="GA">Galanta</option>\n<option value="GL">Gelnica</option>\n<option value="HC">Hlohovec</option>\n<option value="HE">Humenne</option>\n<option value="IL">Ilava</option>\n<option value="KK">Kezmarok</option>\n<option value="KN">Komarno</option>\n<option value="KE1">Kosice I</option>\n<option value="KE2">Kosice II</option>\n<option value="KE3">Kosice III</option>\n<option value="KE4">Kosice IV</option>\n<option value="KEO">Kosice - okolie</option>\n<option value="KA">Krupina</option>\n<option value="KM">Kysucke Nove Mesto</option>\n<option value="LV">Levice</option>\n<option value="LE">Levoca</option>\n<option value="LM">Liptovsky Mikulas</option>\n<option value="LC">Lucenec</option>\n<option value="MA">Malacky</option>\n<option value="MT">Martin</option>\n<option value="ML">Medzilaborce</option>\n<option value="MI">Michalovce</option>\n<option value="MY">Myjava</option>\n<option value="NO">Namestovo</option>\n<option value="NR">Nitra</option>\n<option value="NM">Nove Mesto nad Vahom</option>\n<option value="NZ">Nove Zamky</option>\n<option value="PE">Partizanske</option>\n<option value="PK">Pezinok</option>\n<option value="PN">Piestany</option>\n<option value="PT">Poltar</option>\n<option value="PP">Poprad</option>\n<option value="PB">Povazska Bystrica</option>\n<option value="PO">Presov</option>\n<option value="PD">Prievidza</option>\n<option value="PU">Puchov</option>\n<option value="RA">Revuca</option>\n<option value="RS">Rimavska Sobota</option>\n<option value="RV">Roznava</option>\n<option value="RK" selected="selected">Ruzomberok</option>\n<option value="SB">Sabinov</option>\n<option value="SC">Senec</option>\n<option value="SE">Senica</option>\n<option value="SI">Skalica</option>\n<option value="SV">Snina</option>\n<option value="SO">Sobrance</option>\n<option value="SN">Spisska Nova Ves</option>\n<option value="SL">Stara Lubovna</option>\n<option value="SP">Stropkov</option>\n<option value="SK">Svidnik</option>\n<option value="SA">Sala</option>\n<option value="TO">Topolcany</option>\n<option value="TV">Trebisov</option>\n<option value="TN">Trencin</option>\n<option value="TT">Trnava</option>\n<option value="TR">Turcianske Teplice</option>\n<option value="TS">Tvrdosin</option>\n<option value="VK">Velky Krtis</option>\n<option value="VT">Vranov nad Toplou</option>\n<option value="ZM">Zlate Moravce</option>\n<option value="ZV">Zvolen</option>\n<option value="ZC">Zarnovica</option>\n<option value="ZH">Ziar nad Hronom</option>\n<option value="ZA">Zilina</option>\n</select>'

# PLVoivodeshipSelect ##########################################################

>>> from django.contrib.localflavor.pl.forms import PLVoivodeshipSelect
>>> f = PLVoivodeshipSelect()
>>> f.render('voivodeships','pomerania')
u'<select name="voivodeships">\n<option value="lower_silesia">Lower Silesia</option>\n<option value="kuyavia-pomerania">Kuyavia-Pomerania</option>\n<option value="lublin">Lublin</option>\n<option value="lubusz">Lubusz</option>\n<option value="lodz">Lodz</option>\n<option value="lesser_poland">Lesser Poland</option>\n<option value="masovia">Masovia</option>\n<option value="opole">Opole</option>\n<option value="subcarpatia">Subcarpatia</option>\n<option value="podlasie">Podlasie</option>\n<option value="pomerania" selected="selected">Pomerania</option>\n<option value="silesia">Silesia</option>\n<option value="swietokrzyskie">Swietokrzyskie</option>\n<option value="warmia-masuria">Warmia-Masuria</option>\n<option value="greater_poland">Greater Poland</option>\n<option value="west_pomerania">West Pomerania</option>\n</select>'

# PLAdministrativeUnitSelect ##########################################################

>>> from django.contrib.localflavor.pl.forms import PLAdministrativeUnitSelect
>>> f = PLAdministrativeUnitSelect()
>>> f.render('administrativeunit','katowice')
u'<select name="administrativeunit">\n<option value="wroclaw">Wroc\u0142aw</option>\n<option value="jeleniagora">Jelenia G\xf3ra</option>\n<option value="legnica">Legnica</option>\n<option value="boleslawiecki">boles\u0142awiecki</option>\n<option value="dzierzoniowski">dzier\u017coniowski</option>\n<option value="glogowski">g\u0142ogowski</option>\n<option value="gorowski">g\xf3rowski</option>\n<option value="jaworski">jaworski</option>\n<option value="jeleniogorski">jeleniog\xf3rski</option>\n<option value="kamiennogorski">kamiennog\xf3rski</option>\n<option value="klodzki">k\u0142odzki</option>\n<option value="legnicki">legnicki</option>\n<option value="lubanski">luba\u0144ski</option>\n<option value="lubinski">lubi\u0144ski</option>\n<option value="lwowecki">lw\xf3wecki</option>\n<option value="milicki">milicki</option>\n<option value="olesnicki">ole\u015bnicki</option>\n<option value="olawski">o\u0142awski</option>\n<option value="polkowicki">polkowicki</option>\n<option value="strzelinski">strzeli\u0144ski</option>\n<option value="sredzki">\u015bredzki</option>\n<option value="swidnicki">\u015bwidnicki</option>\n<option value="trzebnicki">trzebnicki</option>\n<option value="walbrzyski">wa\u0142brzyski</option>\n<option value="wolowski">wo\u0142owski</option>\n<option value="wroclawski">wroc\u0142awski</option>\n<option value="zabkowicki">z\u0105bkowicki</option>\n<option value="zgorzelecki">zgorzelecki</option>\n<option value="zlotoryjski">z\u0142otoryjski</option>\n<option value="bydgoszcz">Bydgoszcz</option>\n<option value="torun">Toru\u0144</option>\n<option value="wloclawek">W\u0142oc\u0142awek</option>\n<option value="grudziadz">Grudzi\u0105dz</option>\n<option value="aleksandrowski">aleksandrowski</option>\n<option value="brodnicki">brodnicki</option>\n<option value="bydgoski">bydgoski</option>\n<option value="chelminski">che\u0142mi\u0144ski</option>\n<option value="golubsko-dobrzynski">golubsko-dobrzy\u0144ski</option>\n<option value="grudziadzki">grudzi\u0105dzki</option>\n<option value="inowroclawski">inowroc\u0142awski</option>\n<option value="lipnowski">lipnowski</option>\n<option value="mogilenski">mogile\u0144ski</option>\n<option value="nakielski">nakielski</option>\n<option value="radziejowski">radziejowski</option>\n<option value="rypinski">rypi\u0144ski</option>\n<option value="sepolenski">s\u0119pole\u0144ski</option>\n<option value="swiecki">\u015bwiecki</option>\n<option value="torunski">toru\u0144ski</option>\n<option value="tucholski">tucholski</option>\n<option value="wabrzeski">w\u0105brzeski</option>\n<option value="wloclawski">wroc\u0142awski</option>\n<option value="zninski">\u017ani\u0144ski</option>\n<option value="lublin">Lublin</option>\n<option value="biala-podlaska">Bia\u0142a Podlaska</option>\n<option value="chelm">Che\u0142m</option>\n<option value="zamosc">Zamo\u015b\u0107</option>\n<option value="bialski">bialski</option>\n<option value="bilgorajski">bi\u0142gorajski</option>\n<option value="chelmski">che\u0142mski</option>\n<option value="hrubieszowski">hrubieszowski</option>\n<option value="janowski">janowski</option>\n<option value="krasnostawski">krasnostawski</option>\n<option value="krasnicki">kra\u015bnicki</option>\n<option value="lubartowski">lubartowski</option>\n<option value="lubelski">lubelski</option>\n<option value="leczynski">\u0142\u0119czy\u0144ski</option>\n<option value="lukowski">\u0142ukowski</option>\n<option value="opolski">opolski</option>\n<option value="parczewski">parczewski</option>\n<option value="pulawski">pu\u0142awski</option>\n<option value="radzynski">radzy\u0144ski</option>\n<option value="rycki">rycki</option>\n<option value="swidnicki">\u015bwidnicki</option>\n<option value="tomaszowski">tomaszowski</option>\n<option value="wlodawski">w\u0142odawski</option>\n<option value="zamojski">zamojski</option>\n<option value="gorzow-wielkopolski">Gorz\xf3w Wielkopolski</option>\n<option value="zielona-gora">Zielona G\xf3ra</option>\n<option value="gorzowski">gorzowski</option>\n<option value="krosnienski">kro\u015bnie\u0144ski</option>\n<option value="miedzyrzecki">mi\u0119dzyrzecki</option>\n<option value="nowosolski">nowosolski</option>\n<option value="slubicki">s\u0142ubicki</option>\n<option value="strzelecko-drezdenecki">strzelecko-drezdenecki</option>\n<option value="sulecinski">sule\u0144ci\u0144ski</option>\n<option value="swiebodzinski">\u015bwiebodzi\u0144ski</option>\n<option value="wschowski">wschowski</option>\n<option value="zielonogorski">zielonog\xf3rski</option>\n<option value="zaganski">\u017caga\u0144ski</option>\n<option value="zarski">\u017carski</option>\n<option value="lodz">\u0141\xf3d\u017a</option>\n<option value="piotrkow-trybunalski">Piotrk\xf3w Trybunalski</option>\n<option value="skierniewice">Skierniewice</option>\n<option value="belchatowski">be\u0142chatowski</option>\n<option value="brzezinski">brzezi\u0144ski</option>\n<option value="kutnowski">kutnowski</option>\n<option value="laski">\u0142aski</option>\n<option value="leczycki">\u0142\u0119czycki</option>\n<option value="lowicki">\u0142owicki</option>\n<option value="lodzki wschodni">\u0142\xf3dzki wschodni</option>\n<option value="opoczynski">opoczy\u0144ski</option>\n<option value="pabianicki">pabianicki</option>\n<option value="pajeczanski">paj\u0119cza\u0144ski</option>\n<option value="piotrkowski">piotrkowski</option>\n<option value="poddebicki">podd\u0119bicki</option>\n<option value="radomszczanski">radomszcza\u0144ski</option>\n<option value="rawski">rawski</option>\n<option value="sieradzki">sieradzki</option>\n<option value="skierniewicki">skierniewicki</option>\n<option value="tomaszowski">tomaszowski</option>\n<option value="wielunski">wielu\u0144ski</option>\n<option value="wieruszowski">wieruszowski</option>\n<option value="zdunskowolski">zdu\u0144skowolski</option>\n<option value="zgierski">zgierski</option>\n<option value="krakow">Krak\xf3w</option>\n<option value="tarnow">Tarn\xf3w</option>\n<option value="nowy-sacz">Nowy S\u0105cz</option>\n<option value="bochenski">boche\u0144ski</option>\n<option value="brzeski">brzeski</option>\n<option value="chrzanowski">chrzanowski</option>\n<option value="dabrowski">d\u0105browski</option>\n<option value="gorlicki">gorlicki</option>\n<option value="krakowski">krakowski</option>\n<option value="limanowski">limanowski</option>\n<option value="miechowski">miechowski</option>\n<option value="myslenicki">my\u015blenicki</option>\n<option value="nowosadecki">nowos\u0105decki</option>\n<option value="nowotarski">nowotarski</option>\n<option value="olkuski">olkuski</option>\n<option value="oswiecimski">o\u015bwi\u0119cimski</option>\n<option value="proszowicki">proszowicki</option>\n<option value="suski">suski</option>\n<option value="tarnowski">tarnowski</option>\n<option value="tatrzanski">tatrza\u0144ski</option>\n<option value="wadowicki">wadowicki</option>\n<option value="wielicki">wielicki</option>\n<option value="warszawa">Warszawa</option>\n<option value="ostroleka">Ostro\u0142\u0119ka</option>\n<option value="plock">P\u0142ock</option>\n<option value="radom">Radom</option>\n<option value="siedlce">Siedlce</option>\n<option value="bialobrzeski">bia\u0142obrzeski</option>\n<option value="ciechanowski">ciechanowski</option>\n<option value="garwolinski">garwoli\u0144ski</option>\n<option value="gostyninski">gostyni\u0144ski</option>\n<option value="grodziski">grodziski</option>\n<option value="grojecki">gr\xf3jecki</option>\n<option value="kozienicki">kozenicki</option>\n<option value="legionowski">legionowski</option>\n<option value="lipski">lipski</option>\n<option value="losicki">\u0142osicki</option>\n<option value="makowski">makowski</option>\n<option value="minski">mi\u0144ski</option>\n<option value="mlawski">m\u0142awski</option>\n<option value="nowodworski">nowodworski</option>\n<option value="ostrolecki">ostro\u0142\u0119cki</option>\n<option value="ostrowski">ostrowski</option>\n<option value="otwocki">otwocki</option>\n<option value="piaseczynski">piaseczy\u0144ski</option>\n<option value="plocki">p\u0142ocki</option>\n<option value="plonski">p\u0142o\u0144ski</option>\n<option value="pruszkowski">pruszkowski</option>\n<option value="przasnyski">przasnyski</option>\n<option value="przysuski">przysuski</option>\n<option value="pultuski">pu\u0142tuski</option>\n<option value="radomski">radomski</option>\n<option value="siedlecki">siedlecki</option>\n<option value="sierpecki">sierpecki</option>\n<option value="sochaczewski">sochaczewski</option>\n<option value="sokolowski">soko\u0142owski</option>\n<option value="szydlowiecki">szyd\u0142owiecki</option>\n<option value="warszawski-zachodni">warszawski zachodni</option>\n<option value="wegrowski">w\u0119growski</option>\n<option value="wolominski">wo\u0142omi\u0144ski</option>\n<option value="wyszkowski">wyszkowski</option>\n<option value="zwolenski">zwole\u0144ski</option>\n<option value="zurominski">\u017curomi\u0144ski</option>\n<option value="zyrardowski">\u017cyrardowski</option>\n<option value="opole">Opole</option>\n<option value="brzeski">brzeski</option>\n<option value="glubczycki">g\u0142ubczyski</option>\n<option value="kedzierzynsko-kozielski">k\u0119dzierzy\u0144ski-kozielski</option>\n<option value="kluczborski">kluczborski</option>\n<option value="krapkowicki">krapkowicki</option>\n<option value="namyslowski">namys\u0142owski</option>\n<option value="nyski">nyski</option>\n<option value="oleski">oleski</option>\n<option value="opolski">opolski</option>\n<option value="prudnicki">prudnicki</option>\n<option value="strzelecki">strzelecki</option>\n<option value="rzeszow">Rzesz\xf3w</option>\n<option value="krosno">Krosno</option>\n<option value="przemysl">Przemy\u015bl</option>\n<option value="tarnobrzeg">Tarnobrzeg</option>\n<option value="bieszczadzki">bieszczadzki</option>\n<option value="brzozowski">brzozowski</option>\n<option value="debicki">d\u0119bicki</option>\n<option value="jaroslawski">jaros\u0142awski</option>\n<option value="jasielski">jasielski</option>\n<option value="kolbuszowski">kolbuszowski</option>\n<option value="krosnienski">kro\u015bnie\u0144ski</option>\n<option value="leski">leski</option>\n<option value="lezajski">le\u017cajski</option>\n<option value="lubaczowski">lubaczowski</option>\n<option value="lancucki">\u0142a\u0144cucki</option>\n<option value="mielecki">mielecki</option>\n<option value="nizanski">ni\u017ca\u0144ski</option>\n<option value="przemyski">przemyski</option>\n<option value="przeworski">przeworski</option>\n<option value="ropczycko-sedziszowski">ropczycko-s\u0119dziszowski</option>\n<option value="rzeszowski">rzeszowski</option>\n<option value="sanocki">sanocki</option>\n<option value="stalowowolski">stalowowolski</option>\n<option value="strzyzowski">strzy\u017cowski</option>\n<option value="tarnobrzeski">tarnobrzeski</option>\n<option value="bialystok">Bia\u0142ystok</option>\n<option value="lomza">\u0141om\u017ca</option>\n<option value="suwalki">Suwa\u0142ki</option>\n<option value="augustowski">augustowski</option>\n<option value="bialostocki">bia\u0142ostocki</option>\n<option value="bielski">bielski</option>\n<option value="grajewski">grajewski</option>\n<option value="hajnowski">hajnowski</option>\n<option value="kolnenski">kolne\u0144ski</option>\n<option value="\u0142omzynski">\u0142om\u017cy\u0144ski</option>\n<option value="moniecki">moniecki</option>\n<option value="sejnenski">sejne\u0144ski</option>\n<option value="siemiatycki">siematycki</option>\n<option value="sokolski">sok\xf3lski</option>\n<option value="suwalski">suwalski</option>\n<option value="wysokomazowiecki">wysokomazowiecki</option>\n<option value="zambrowski">zambrowski</option>\n<option value="gdansk">Gda\u0144sk</option>\n<option value="gdynia">Gdynia</option>\n<option value="slupsk">S\u0142upsk</option>\n<option value="sopot">Sopot</option>\n<option value="bytowski">bytowski</option>\n<option value="chojnicki">chojnicki</option>\n<option value="czluchowski">cz\u0142uchowski</option>\n<option value="kartuski">kartuski</option>\n<option value="koscierski">ko\u015bcierski</option>\n<option value="kwidzynski">kwidzy\u0144ski</option>\n<option value="leborski">l\u0119borski</option>\n<option value="malborski">malborski</option>\n<option value="nowodworski">nowodworski</option>\n<option value="gdanski">gda\u0144ski</option>\n<option value="pucki">pucki</option>\n<option value="slupski">s\u0142upski</option>\n<option value="starogardzki">starogardzki</option>\n<option value="sztumski">sztumski</option>\n<option value="tczewski">tczewski</option>\n<option value="wejherowski">wejcherowski</option>\n<option value="katowice" selected="selected">Katowice</option>\n<option value="bielsko-biala">Bielsko-Bia\u0142a</option>\n<option value="bytom">Bytom</option>\n<option value="chorzow">Chorz\xf3w</option>\n<option value="czestochowa">Cz\u0119stochowa</option>\n<option value="dabrowa-gornicza">D\u0105browa G\xf3rnicza</option>\n<option value="gliwice">Gliwice</option>\n<option value="jastrzebie-zdroj">Jastrz\u0119bie Zdr\xf3j</option>\n<option value="jaworzno">Jaworzno</option>\n<option value="myslowice">Mys\u0142owice</option>\n<option value="piekary-slaskie">Piekary \u015al\u0105skie</option>\n<option value="ruda-slaska">Ruda \u015al\u0105ska</option>\n<option value="rybnik">Rybnik</option>\n<option value="siemianowice-slaskie">Siemianowice \u015al\u0105skie</option>\n<option value="sosnowiec">Sosnowiec</option>\n<option value="swietochlowice">\u015awi\u0119toch\u0142owice</option>\n<option value="tychy">Tychy</option>\n<option value="zabrze">Zabrze</option>\n<option value="zory">\u017bory</option>\n<option value="bedzinski">b\u0119dzi\u0144ski</option>\n<option value="bielski">bielski</option>\n<option value="bierunsko-ledzinski">bieru\u0144sko-l\u0119dzi\u0144ski</option>\n<option value="cieszynski">cieszy\u0144ski</option>\n<option value="czestochowski">cz\u0119stochowski</option>\n<option value="gliwicki">gliwicki</option>\n<option value="klobucki">k\u0142obucki</option>\n<option value="lubliniecki">lubliniecki</option>\n<option value="mikolowski">miko\u0142owski</option>\n<option value="myszkowski">myszkowski</option>\n<option value="pszczynski">pszczy\u0144ski</option>\n<option value="raciborski">raciborski</option>\n<option value="rybnicki">rybnicki</option>\n<option value="tarnogorski">tarnog\xf3rski</option>\n<option value="wodzislawski">wodzis\u0142awski</option>\n<option value="zawiercianski">zawiercia\u0144ski</option>\n<option value="zywiecki">\u017cywiecki</option>\n<option value="kielce">Kielce</option>\n<option value="buski">buski</option>\n<option value="jedrzejowski">j\u0119drzejowski</option>\n<option value="kazimierski">kazimierski</option>\n<option value="kielecki">kielecki</option>\n<option value="konecki">konecki</option>\n<option value="opatowski">opatowski</option>\n<option value="ostrowiecki">ostrowiecki</option>\n<option value="pinczowski">pi\u0144czowski</option>\n<option value="sandomierski">sandomierski</option>\n<option value="skarzyski">skar\u017cyski</option>\n<option value="starachowicki">starachowicki</option>\n<option value="staszowski">staszowski</option>\n<option value="wloszczowski">w\u0142oszczowski</option>\n<option value="olsztyn">Olsztyn</option>\n<option value="elblag">Elbl\u0105g</option>\n<option value="bartoszycki">bartoszycki</option>\n<option value="braniewski">braniewski</option>\n<option value="dzialdowski">dzia\u0142dowski</option>\n<option value="elblaski">elbl\u0105ski</option>\n<option value="elcki">e\u0142cki</option>\n<option value="gizycki">gi\u017cycki</option>\n<option value="goldapski">go\u0142dapski</option>\n<option value="ilawski">i\u0142awski</option>\n<option value="ketrzynski">k\u0119trzy\u0144ski</option>\n<option value="lidzbarski">lidzbarski</option>\n<option value="mragowski">mr\u0105gowski</option>\n<option value="nidzicki">nidzicki</option>\n<option value="nowomiejski">nowomiejski</option>\n<option value="olecki">olecki</option>\n<option value="olsztynski">olszty\u0144ski</option>\n<option value="ostrodzki">ostr\xf3dzki</option>\n<option value="piski">piski</option>\n<option value="szczycienski">szczycie\u0144ski</option>\n<option value="wegorzewski">w\u0119gorzewski</option>\n<option value="poznan">Pozna\u0144</option>\n<option value="kalisz">Kalisz</option>\n<option value="konin">Konin</option>\n<option value="leszno">Leszno</option>\n<option value="chodzieski">chodziejski</option>\n<option value="czarnkowsko-trzcianecki">czarnkowsko-trzcianecki</option>\n<option value="gnieznienski">gnie\u017anie\u0144ski</option>\n<option value="gostynski">gosty\u0144ski</option>\n<option value="grodziski">grodziski</option>\n<option value="jarocinski">jaroci\u0144ski</option>\n<option value="kaliski">kaliski</option>\n<option value="kepinski">k\u0119pi\u0144ski</option>\n<option value="kolski">kolski</option>\n<option value="koninski">koni\u0144ski</option>\n<option value="koscianski">ko\u015bcia\u0144ski</option>\n<option value="krotoszynski">krotoszy\u0144ski</option>\n<option value="leszczynski">leszczy\u0144ski</option>\n<option value="miedzychodzki">mi\u0119dzychodzki</option>\n<option value="nowotomyski">nowotomyski</option>\n<option value="obornicki">obornicki</option>\n<option value="ostrowski">ostrowski</option>\n<option value="ostrzeszowski">ostrzeszowski</option>\n<option value="pilski">pilski</option>\n<option value="pleszewski">pleszewski</option>\n<option value="poznanski">pozna\u0144ski</option>\n<option value="rawicki">rawicki</option>\n<option value="slupecki">s\u0142upecki</option>\n<option value="szamotulski">szamotulski</option>\n<option value="sredzki">\u015bredzki</option>\n<option value="sremski">\u015bremski</option>\n<option value="turecki">turecki</option>\n<option value="wagrowiecki">w\u0105growiecki</option>\n<option value="wolsztynski">wolszty\u0144ski</option>\n<option value="wrzesinski">wrzesi\u0144ski</option>\n<option value="zlotowski">z\u0142otowski</option>\n<option value="bialogardzki">bia\u0142ogardzki</option>\n<option value="choszczenski">choszcze\u0144ski</option>\n<option value="drawski">drawski</option>\n<option value="goleniowski">goleniowski</option>\n<option value="gryficki">gryficki</option>\n<option value="gryfinski">gryfi\u0144ski</option>\n<option value="kamienski">kamie\u0144ski</option>\n<option value="kolobrzeski">ko\u0142obrzeski</option>\n<option value="koszalinski">koszali\u0144ski</option>\n<option value="lobeski">\u0142obeski</option>\n<option value="mysliborski">my\u015bliborski</option>\n<option value="policki">policki</option>\n<option value="pyrzycki">pyrzycki</option>\n<option value="slawienski">s\u0142awie\u0144ski</option>\n<option value="stargardzki">stargardzki</option>\n<option value="szczecinecki">szczecinecki</option>\n<option value="swidwinski">\u015bwidwi\u0144ski</option>\n<option value="walecki">wa\u0142ecki</option>\n</select>'

# PLPostalCodeField ##############################################################

>>> from django.contrib.localflavor.pl.forms import PLPostalCodeField
>>> f = PLPostalCodeField()
>>> f.clean('43--434')
Traceback (most recent call last):
...
ValidationError: [u'Enter a postal code in the format XX-XXX.']
>>> f.clean('41-403')
u'41-403'

# PLTaxNumberField ###############################################################

>>> from django.contrib.localflavor.pl.forms import PLTaxNumberField
>>> f = PLTaxNumberField()
>>> f.clean('43-343-234-323')
Traceback (most recent call last):
...
ValidationError: [u'Enter a tax number field (NIP) in the format XXX-XXX-XX-XX or XX-XX-XXX-XXX.']
>>> f.clean('43-34-234-323')
u'43-34-234-323'
>>> f.clean('433-344-24-23')
u'433-344-24-23'

# PLNationalIdentificationNumberField ############################################

>>> from django.contrib.localflavor.pl.forms import PLNationalIdentificationNumberField
>>> f =  PLNationalIdentificationNumberField()
>>> f.clean('80071610614')
u'80071610614'
>>> f.clean('80071610610')
Traceback (most recent call last):
...
ValidationError: [u'Wrong checksum for the National Identification Number.']
>>> f.clean('80')
Traceback (most recent call last):
...
ValidationError: [u'National Identification Number consists of 11 digits.']
>>> f.clean('800716106AA')
Traceback (most recent call last):
...
ValidationError: [u'National Identification Number consists of 11 digits.']

# NLPhoneNumberField ########################################################

>>> from django.contrib.localflavor.nl.forms import NLPhoneNumberField
>>> f = NLPhoneNumberField(required=False)
>>> f.clean('')
u''
>>> f.clean('012-3456789')
'012-3456789'
>>> f.clean('0123456789')
'0123456789'
>>> f.clean('+31-12-3456789')
'+31-12-3456789'
>>> f.clean('(0123) 456789')
'(0123) 456789'
>>> f.clean('foo')
Traceback (most recent call last):
    ...
ValidationError: [u'Enter a valid phone number']

# NLZipCodeField ############################################################

>>> from django.contrib.localflavor.nl.forms import NLZipCodeField
>>> f = NLZipCodeField(required=False)
>>> f.clean('')
u''
>>> f.clean('1234ab')
u'1234 AB'
>>> f.clean('1234 ab')
u'1234 AB'
>>> f.clean('1234 AB')
u'1234 AB'
>>> f.clean('0123AB')
Traceback (most recent call last):
    ...
ValidationError: [u'Enter a valid postal code']
>>> f.clean('foo')
Traceback (most recent call last):
    ...
ValidationError: [u'Enter a valid postal code']

# NLSoFiNumberField #########################################################

>>> from django.contrib.localflavor.nl.forms import NLSoFiNumberField
>>> f = NLSoFiNumberField(required=False)
>>> f.clean('')
u''
>>> f.clean('123456782')
'123456782'
>>> f.clean('000000000')
Traceback (most recent call last):
    ...
ValidationError: [u'Enter a valid SoFi number']
>>> f.clean('123456789')
Traceback (most recent call last):
    ...
ValidationError: [u'Enter a valid SoFi number']
>>> f.clean('foo')
Traceback (most recent call last):
    ...
ValidationError: [u'Enter a valid SoFi number']

# NLProvinceSelect ##########################################################

>>> from django.contrib.localflavor.nl.forms import NLProvinceSelect
>>> s = NLProvinceSelect()
>>> s.render('provinces', 'OV')
u'<select name="provinces">\n<option value="DR">Drente</option>\n<option value="FL">Flevoland</option>\n<option value="FR">Friesland</option>\n<option value="GL">Gelderland</option>\n<option value="GR">Groningen</option>\n<option value="LB">Limburg</option>\n<option value="NB">Noord-Brabant</option>\n<option value="NH">Noord-Holland</option>\n<option value="OV" selected="selected">Overijssel</option>\n<option value="UT">Utrecht</option>\n<option value="ZE">Zeeland</option>\n<option value="ZH">Zuid-Holland</option>\n</select>'

# ARProvinceField #############################################################

>>> from django.contrib.localflavor.ar.forms import ARProvinceSelect
>>> f = ARProvinceSelect()
>>> f.render('provincias', 'A')
u'<select name="provincias">\n<option value="B">Buenos Aires</option>\n<option value="K">Catamarca</option>\n<option value="H">Chaco</option>\n<option value="U">Chubut</option>\n<option value="C">Ciudad Aut\xf3noma de Buenos Aires</option>\n<option value="X">C\xf3rdoba</option>\n<option value="W">Corrientes</option>\n<option value="E">Entre R\xedos</option>\n<option value="P">Formosa</option>\n<option value="Y">Jujuy</option>\n<option value="L">La Pampa</option>\n<option value="F">La Rioja</option>\n<option value="M">Mendoza</option>\n<option value="N">Misiones</option>\n<option value="Q">Neuqu\xe9n</option>\n<option value="R">R\xedo Negro</option>\n<option value="A" selected="selected">Salta</option>\n<option value="J">San Juan</option>\n<option value="D">San Luis</option>\n<option value="Z">Santa Cruz</option>\n<option value="S">Santa Fe</option>\n<option value="G">Santiago del Estero</option>\n<option value="V">Tierra del Fuego, Ant\xe1rtida e Islas del Atl\xe1ntico Sur</option>\n<option value="T">Tucum\xe1n</option>\n</select>'

# ARPostalCodeField ###########################################################

>>> from django.contrib.localflavor.ar.forms import ARPostalCodeField
>>> f = ARPostalCodeField()
>>> f.clean('5000')
u'5000'
>>> f.clean('C1064AAB')
u'C1064AAB'
>>> f.clean('c1064AAB')
u'C1064AAB'
>>> f.clean('C1064aab')
u'C1064AAB'
>>> f.clean(u'4400')
u'4400'
>>> f.clean(u'C1064AAB')
u'C1064AAB'
>>> f.clean('C1064AABB')
Traceback (most recent call last):
...
ValidationError: [u'Ensure this value has at most 8 characters (it has 9).']
>>> f.clean('C1064AA')
Traceback (most recent call last):
...
ValidationError: [u'Enter a postal code in the format NNNN or ANNNNAAA.']
>>> f.clean('C106AAB')
Traceback (most recent call last):
...
ValidationError: [u'Enter a postal code in the format NNNN or ANNNNAAA.']
>>> f.clean('106AAB')
Traceback (most recent call last):
...
ValidationError: [u'Enter a postal code in the format NNNN or ANNNNAAA.']
>>> f.clean('500')
Traceback (most recent call last):
...
ValidationError: [u'Ensure this value has at least 4 characters (it has 3).']
>>> f.clean('5PPP')
Traceback (most recent call last):
...
ValidationError: [u'Enter a postal code in the format NNNN or ANNNNAAA.']
>>> f.clean(None)
Traceback (most recent call last):
...
ValidationError: [u'This field is required.']
>>> f.clean('')
Traceback (most recent call last):
...
ValidationError: [u'This field is required.']
>>> f.clean(u'')
Traceback (most recent call last):
...
ValidationError: [u'This field is required.']

>>> f = ARPostalCodeField(required=False)
>>> f.clean('5000')
u'5000'
>>> f.clean('C1064AAB')
u'C1064AAB'
>>> f.clean('c1064AAB')
u'C1064AAB'
>>> f.clean('C1064aab')
u'C1064AAB'
>>> f.clean(u'4400')
u'4400'
>>> f.clean(u'C1064AAB')
u'C1064AAB'
>>> f.clean('C1064AABB')
Traceback (most recent call last):
...
ValidationError: [u'Ensure this value has at most 8 characters (it has 9).']
>>> f.clean('C1064AA')
Traceback (most recent call last):
...
ValidationError: [u'Enter a postal code in the format NNNN or ANNNNAAA.']
>>> f.clean('C106AAB')
Traceback (most recent call last):
...
ValidationError: [u'Enter a postal code in the format NNNN or ANNNNAAA.']
>>> f.clean('106AAB')
Traceback (most recent call last):
...
ValidationError: [u'Enter a postal code in the format NNNN or ANNNNAAA.']
>>> f.clean('500')
Traceback (most recent call last):
...
ValidationError: [u'Ensure this value has at least 4 characters (it has 3).']
>>> f.clean('5PPP')
Traceback (most recent call last):
...
ValidationError: [u'Enter a postal code in the format NNNN or ANNNNAAA.']
>>> f.clean(None)
u''
>>> f.clean('')
u''
>>> f.clean(u'')
u''

# ARDNIField ##################################################################

>>> from django.contrib.localflavor.ar.forms import ARDNIField
>>> f = ARDNIField()
>>> f.clean('20123456')
u'20123456'
>>> f.clean('20.123.456')
u'20123456'
>>> f.clean('9123456')
u'9123456'
>>> f.clean('9.123.456')
u'9123456'
>>> f.clean(u'20123456')
u'20123456'
>>> f.clean(u'20.123.456')
u'20123456'
>>> f.clean('20.123456')
u'20123456'
>>> f.clean('101234566')
Traceback (most recent call last):
...
ValidationError: [u'This field requires 7 or 8 digits.']
>>> f.clean('W0123456')
Traceback (most recent call last):
...
ValidationError: [u'This field requires only numbers.']
>>> f.clean('10,123,456')
Traceback (most recent call last):
...
ValidationError: [u'This field requires only numbers.']
>>> f.clean(None)
Traceback (most recent call last):
...
ValidationError: [u'This field is required.']
>>> f.clean('')
Traceback (most recent call last):
...
ValidationError: [u'This field is required.']
>>> f.clean(u'')
Traceback (most recent call last):
...
ValidationError: [u'This field is required.']

>>> f = ARDNIField(required=False)
>>> f.clean('20123456')
u'20123456'
>>> f.clean('20.123.456')
u'20123456'
>>> f.clean('9123456')
u'9123456'
>>> f.clean('9.123.456')
u'9123456'
>>> f.clean(u'20123456')
u'20123456'
>>> f.clean(u'20.123.456')
u'20123456'
>>> f.clean('20.123456')
u'20123456'
>>> f.clean('101234566')
Traceback (most recent call last):
...
ValidationError: [u'This field requires 7 or 8 digits.']
>>> f.clean('W0123456')
Traceback (most recent call last):
...
ValidationError: [u'This field requires only numbers.']
>>> f.clean('10,123,456')
Traceback (most recent call last):
...
ValidationError: [u'This field requires only numbers.']
>>> f.clean(None)
u''
>>> f.clean('')
u''
>>> f.clean(u'')
u''

# ARCUITField #################################################################

>>> from django.contrib.localflavor.ar.forms import ARCUITField
>>> f = ARCUITField()
>>> f.clean('20-10123456-9')
u'20-10123456-9'
>>> f.clean(u'20-10123456-9')
u'20-10123456-9'
>>> f.clean('27-10345678-4')
u'27-10345678-4'
>>> f.clean('20101234569')
u'20-10123456-9'
>>> f.clean('27103456784')
u'27-10345678-4'
>>> f.clean('2-10123456-9')
Traceback (most recent call last):
...
ValidationError: [u'Enter a valid CUIT in XX-XXXXXXXX-X or XXXXXXXXXXXX format.']
>>> f.clean('210123456-9')
Traceback (most recent call last):
...
ValidationError: [u'Enter a valid CUIT in XX-XXXXXXXX-X or XXXXXXXXXXXX format.']
>>> f.clean('20-10123456')
Traceback (most recent call last):
...
ValidationError: [u'Enter a valid CUIT in XX-XXXXXXXX-X or XXXXXXXXXXXX format.']
>>> f.clean('20-10123456-')
Traceback (most recent call last):
...
ValidationError: [u'Enter a valid CUIT in XX-XXXXXXXX-X or XXXXXXXXXXXX format.']
>>> f.clean('20-10123456-5')
Traceback (most recent call last):
...
ValidationError: [u'Invalid CUIT.']
>>> f.clean(u'2-10123456-9')
Traceback (most recent call last):
...
ValidationError: [u'Enter a valid CUIT in XX-XXXXXXXX-X or XXXXXXXXXXXX format.']
>>> f.clean('27-10345678-1')
Traceback (most recent call last):
...
ValidationError: [u'Invalid CUIT.']
>>> f.clean(u'27-10345678-1')
Traceback (most recent call last):
...
ValidationError: [u'Invalid CUIT.']
>>> f.clean(None)
Traceback (most recent call last):
...
ValidationError: [u'This field is required.']
>>> f.clean('')
Traceback (most recent call last):
...
ValidationError: [u'This field is required.']
>>> f.clean(u'')
Traceback (most recent call last):
...
ValidationError: [u'This field is required.']

>>> f = ARCUITField(required=False)
>>> f.clean('20-10123456-9')
u'20-10123456-9'
>>> f.clean(u'20-10123456-9')
u'20-10123456-9'
>>> f.clean('27-10345678-4')
u'27-10345678-4'
>>> f.clean('20101234569')
u'20-10123456-9'
>>> f.clean('27103456784')
u'27-10345678-4'
>>> f.clean('2-10123456-9')
Traceback (most recent call last):
...
ValidationError: [u'Enter a valid CUIT in XX-XXXXXXXX-X or XXXXXXXXXXXX format.']
>>> f.clean('210123456-9')
Traceback (most recent call last):
...
ValidationError: [u'Enter a valid CUIT in XX-XXXXXXXX-X or XXXXXXXXXXXX format.']
>>> f.clean('20-10123456')
Traceback (most recent call last):
...
ValidationError: [u'Enter a valid CUIT in XX-XXXXXXXX-X or XXXXXXXXXXXX format.']
>>> f.clean('20-10123456-')
Traceback (most recent call last):
...
ValidationError: [u'Enter a valid CUIT in XX-XXXXXXXX-X or XXXXXXXXXXXX format.']
>>> f.clean('20-10123456-5')
Traceback (most recent call last):
...
ValidationError: [u'Invalid CUIT.']
>>> f.clean(u'2-10123456-9')
Traceback (most recent call last):
...
ValidationError: [u'Enter a valid CUIT in XX-XXXXXXXX-X or XXXXXXXXXXXX format.']
>>> f.clean('27-10345678-1')
Traceback (most recent call last):
...
ValidationError: [u'Invalid CUIT.']
>>> f.clean(u'27-10345678-1')
Traceback (most recent call last):
...
ValidationError: [u'Invalid CUIT.']
>>> f.clean(None)
u''
>>> f.clean('')
u''
>>> f.clean(u'')
u''

# CAPostalCodeField ##############################################################

CAPostalCodeField validates that the data is a six-character Canadian postal code.
>>> from django.contrib.localflavor.ca.forms import CAPostalCodeField
>>> f = CAPostalCodeField()
>>> f.clean('T2S 2H7')
u'T2S 2H7'
>>> f.clean('T2S 2H')
Traceback (most recent call last):
...
ValidationError: [u'Enter a postal code in the format XXX XXX.']
>>> f.clean('2T6 H8I')
Traceback (most recent call last):
...
ValidationError: [u'Enter a postal code in the format XXX XXX.']
>>> f.clean('T2S2H')
Traceback (most recent call last):
...
ValidationError: [u'Enter a postal code in the format XXX XXX.']
>>> f.clean(90210)
Traceback (most recent call last):
...
ValidationError: [u'Enter a postal code in the format XXX XXX.']
>>> f.clean(None)
Traceback (most recent call last):
...
ValidationError: [u'This field is required.']
>>> f.clean('')
Traceback (most recent call last):
...
ValidationError: [u'This field is required.']
>>> f = CAPostalCodeField(required=False)
>>> f.clean('T2S 2H7')
u'T2S 2H7'
>>> f.clean('T2S2H7')
Traceback (most recent call last):
...
ValidationError: [u'Enter a postal code in the format XXX XXX.']
>>> f.clean('T2S 2H')
Traceback (most recent call last):
...
ValidationError: [u'Enter a postal code in the format XXX XXX.']
>>> f.clean('2T6 H8I')
Traceback (most recent call last):
...
ValidationError: [u'Enter a postal code in the format XXX XXX.']
>>> f.clean('T2S2H')
Traceback (most recent call last):
...
ValidationError: [u'Enter a postal code in the format XXX XXX.']
>>> f.clean(90210)
Traceback (most recent call last):
...
ValidationError: [u'Enter a postal code in the format XXX XXX.']
>>> f.clean(None)
u''
>>> f.clean('')
u''

# CAPhoneNumberField ##########################################################

CAPhoneNumberField validates that the data is a valid Canadian phone number,
including the area code. It's normalized to XXX-XXX-XXXX format.
Note: This test is exactly the same as the USPhoneNumberField except using a real
Candian area code

>>> from django.contrib.localflavor.ca.forms import CAPhoneNumberField
>>> f = CAPhoneNumberField()
>>> f.clean('403-555-1212')
u'403-555-1212'
>>> f.clean('4035551212')
u'403-555-1212'
>>> f.clean('403 555-1212')
u'403-555-1212'
>>> f.clean('(403) 555-1212')
u'403-555-1212'
>>> f.clean('403 555 1212')
u'403-555-1212'
>>> f.clean('403.555.1212')
u'403-555-1212'
>>> f.clean('403.555-1212')
u'403-555-1212'
>>> f.clean(' (403) 555.1212 ')
u'403-555-1212'
>>> f.clean('555-1212')
Traceback (most recent call last):
...
ValidationError: [u'Phone numbers must be in XXX-XXX-XXXX format.']
>>> f.clean('403-55-1212')
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

>>> f = CAPhoneNumberField(required=False)
>>> f.clean('403-555-1212')
u'403-555-1212'
>>> f.clean('4035551212')
u'403-555-1212'
>>> f.clean('403 555-1212')
u'403-555-1212'
>>> f.clean('(403) 555-1212')
u'403-555-1212'
>>> f.clean('403 555 1212')
u'403-555-1212'
>>> f.clean('403.555.1212')
u'403-555-1212'
>>> f.clean('403.555-1212')
u'403-555-1212'
>>> f.clean(' (403) 555.1212 ')
u'403-555-1212'
>>> f.clean('555-1212')
Traceback (most recent call last):
...
ValidationError: [u'Phone numbers must be in XXX-XXX-XXXX format.']
>>> f.clean('403-55-1212')
Traceback (most recent call last):
...
ValidationError: [u'Phone numbers must be in XXX-XXX-XXXX format.']
>>> f.clean(None)
u''
>>> f.clean('')
u''

# CAProvinceField ################################################################

CAProvinceField validates that the data is either an abbreviation or name of a
Canadian province.
>>> from django.contrib.localflavor.ca.forms import CAProvinceField
>>> f = CAProvinceField()
>>> f.clean('ab')
u'AB'
>>> f.clean('BC')
u'BC'
>>> f.clean('nova scotia')
u'NS'
>>> f.clean('  manitoba ')
u'MB'
>>> f.clean('T2S 2H7')
Traceback (most recent call last):
...
ValidationError: [u'Enter a Canadian province or territory.']
>>> f.clean(None)
Traceback (most recent call last):
...
ValidationError: [u'This field is required.']
>>> f.clean('')
Traceback (most recent call last):
...
ValidationError: [u'This field is required.']

>>> f = CAProvinceField(required=False)
>>> f.clean('ab')
u'AB'
>>> f.clean('BC')
u'BC'
>>> f.clean('nova scotia')
u'NS'
>>> f.clean('  manitoba ')
u'MB'
>>> f.clean('T2S 2H7')
Traceback (most recent call last):
...
ValidationError: [u'Enter a Canadian province or territory.']
>>> f.clean(None)
u''
>>> f.clean('')
u''

# CAProvinceSelect ###############################################################

CAProvinceSelect is a Select widget that uses a list of Canadian provinces/territories
as its choices.
>>> from django.contrib.localflavor.ca.forms import CAProvinceSelect
>>> w = CAProvinceSelect()
>>> print w.render('province', 'AB')
<select name="province">
<option value="AB" selected="selected">Alberta</option>
<option value="BC">British Columbia</option>
<option value="MB">Manitoba</option>
<option value="NB">New Brunswick</option>
<option value="NF">Newfoundland and Labrador</option>
<option value="NT">Northwest Territories</option>
<option value="NS">Nova Scotia</option>
<option value="NU">Nunavut</option>
<option value="ON">Ontario</option>
<option value="PE">Prince Edward Island</option>
<option value="QC">Quebec</option>
<option value="SK">Saskatchewan</option>
<option value="YK">Yukon</option>
</select>

# CASocialInsuranceNumberField #################################################
>>> from django.contrib.localflavor.ca.forms import CASocialInsuranceNumberField
>>> f = CASocialInsuranceNumberField()
>>> f.clean('046-454-286')
u'046-454-286'
>>> f.clean('046-454-287')
Traceback (most recent call last):
...
ValidationError: [u'Enter a valid Canadian Social Insurance number in XXX-XXX-XXXX format.']
>>> f.clean('046 454 286')
Traceback (most recent call last):
...
ValidationError: [u'Enter a valid Canadian Social Insurance number in XXX-XXX-XXXX format.']
>>> f.clean('046-44-286')
Traceback (most recent call last):
...
ValidationError: [u'Enter a valid Canadian Social Insurance number in XXX-XXX-XXXX format.']

"""
