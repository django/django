from django.contrib.localflavor.jp.forms import (JPPostalCodeField,
    JPPrefectureSelect)

from utils import LocalFlavorTestCase


class JPLocalFlavorTests(LocalFlavorTestCase):
    def test_JPPrefectureSelect(self):
        f = JPPrefectureSelect()
        out = u'''<select name="prefecture">
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
</select>'''
        self.assertEqual(f.render('prefecture', 'kanagawa'), out)

    def test_JPPostalCodeField(self):
        error_format = [u'Enter a postal code in the format XXXXXXX or XXX-XXXX.']
        valid = {
                '251-0032': '2510032',
                '2510032': '2510032',
        }
        invalid = {
                '2510-032': error_format,
                '251a0032': error_format,
                'a51-0032': error_format,
                '25100321': error_format,
        }
        self.assertFieldOutput(JPPostalCodeField, valid, invalid)
