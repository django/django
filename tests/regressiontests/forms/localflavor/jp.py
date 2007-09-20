# -*- coding: utf-8 -*-
# Tests for the contrib/localflavor/ JP form fields.

tests = r"""
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
"""
