# -*- coding: utf-8 -*-
# Tests for the contrib/localflavor/ IS form fields.

tests = r"""
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
ValidationError: [u'Ensure this value has at least 10 characters (it has 9).', u'Enter a valid Icelandic identification number. The format is XXXXXX-XXXX.']
>>> f.clean('230880343234')
Traceback (most recent call last):
...
ValidationError: [u'Ensure this value has at most 11 characters (it has 12).', u'Enter a valid Icelandic identification number. The format is XXXXXX-XXXX.']
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
ValidationError: [u'Ensure this value has at least 7 characters (it has 6).', u'Enter a valid value.']
>>> f.clean('123456555')
Traceback (most recent call last):
...
ValidationError: [u'Ensure this value has at most 8 characters (it has 9).', u'Enter a valid value.']
>>> f.clean('abcdefg')
Traceback (most recent call last):
ValidationError: [u'Enter a valid value.']
>>> f.clean(' 1234567 ')
Traceback (most recent call last):
...
ValidationError: [u'Ensure this value has at most 8 characters (it has 9).', u'Enter a valid value.']
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
"""

