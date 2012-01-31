from django.contrib.localflavor.ru.forms import *

from django.test import SimpleTestCase


class RULocalFlavorTests(SimpleTestCase):

    def test_RUPassportNumberField(self):
        error = [u'Enter a passport number in the format XXXX XXXXXX.']
        valid = {
            '1981 211204': '1981 211204',
            '0305 967876': '0305 967876',
        }
        invalid = {
            '1981 2112044': error,
            '1981 23220': error,
            '9981211201': error,
        }
        self.assertFieldOutput(RUPassportNumberField, valid, invalid)

    def test_RUAlienPassportNumberField(self):
        error = [u'Enter a passport number in the format XX XXXXXXX.']
        valid = {
            '19 8111204': '19 8111204',
            '03 0567876': '03 0567876',
        }
        invalid = {
            '198 1112044': error,
            '19 81123220': error,
            '99 812112': error,
        }
        self.assertFieldOutput(RUAlienPassportNumberField, valid, invalid)

    def test_RUPostalCodeField(self):
        error = [u'Enter a postal code in the format XXXXXX.']
        valid = {
            '987654': '987654',
            '123456': '123456'
        }
        invalid = {
            '123 34': error,
            '1234567': error,
            '12345': error
        }
        self.assertFieldOutput(RUPostalCodeField, valid, invalid)

    def test_RUCountySelect(self):
        f = RUCountySelect()
        out = u'''<select name="county">
<option value="Central Federal County">Central Federal County</option>
<option value="South Federal County">South Federal County</option>
<option value="North-West Federal County">North-West Federal County</option>
<option value="Far-East Federal County">Far-East Federal County</option>
<option value="Siberian Federal County">Siberian Federal County</option>
<option value="Ural Federal County">Ural Federal County</option>
<option value="Privolzhsky Federal County">Privolzhsky Federal County</option>
<option value="North-Caucasian Federal County">North-Caucasian Federal County</option>
</select>'''
        self.assertHTMLEqual(f.render('county', None), out)

    def test_RURegionSelect(self):
        f = RURegionSelect()
        out = u'''<select name="region">
<option value="77">Moskva</option>
<option value="78">Saint-Peterburg</option>
<option value="50">Moskovskaya oblast&#39;</option>
<option value="01">Adygeya, Respublika</option>
<option value="02">Bashkortostan, Respublika</option>
<option value="03">Buryatia, Respublika</option>
<option value="04">Altay, Respublika</option>
<option value="05">Dagestan, Respublika</option>
<option value="06">Ingushskaya Respublika</option>
<option value="07">Kabardino-Balkarskaya Respublika</option>
<option value="08">Kalmykia, Respublika</option>
<option value="09">Karachaevo-Cherkesskaya Respublika</option>
<option value="10">Karelia, Respublika</option>
<option value="11">Komi, Respublika</option>
<option value="12">Mariy Ehl, Respublika</option>
<option value="13">Mordovia, Respublika</option>
<option value="14">Sakha, Respublika (Yakutiya)</option>
<option value="15">Severnaya Osetia, Respublika (Alania)</option>
<option value="16">Tatarstan, Respublika</option>
<option value="17">Tyva, Respublika (Tuva)</option>
<option value="18">Udmurtskaya Respublika</option>
<option value="19">Khakassiya, Respublika</option>
<option value="95">Chechenskaya Respublika</option>
<option value="21">Chuvashskaya Respublika</option>
<option value="22">Altayskiy Kray</option>
<option value="80">Zabaykalskiy Kray</option>
<option value="82">Kamchatskiy Kray</option>
<option value="23">Krasnodarskiy Kray</option>
<option value="24">Krasnoyarskiy Kray</option>
<option value="81">Permskiy Kray</option>
<option value="25">Primorskiy Kray</option>
<option value="26">Stavropol&#39;siyy Kray</option>
<option value="27">Khabarovskiy Kray</option>
<option value="28">Amurskaya oblast&#39;</option>
<option value="29">Arkhangel&#39;skaya oblast&#39;</option>
<option value="30">Astrakhanskaya oblast&#39;</option>
<option value="31">Belgorodskaya oblast&#39;</option>
<option value="32">Bryanskaya oblast&#39;</option>
<option value="33">Vladimirskaya oblast&#39;</option>
<option value="34">Volgogradskaya oblast&#39;</option>
<option value="35">Vologodskaya oblast&#39;</option>
<option value="36">Voronezhskaya oblast&#39;</option>
<option value="37">Ivanovskaya oblast&#39;</option>
<option value="38">Irkutskaya oblast&#39;</option>
<option value="39">Kaliningradskaya oblast&#39;</option>
<option value="40">Kaluzhskaya oblast&#39;</option>
<option value="42">Kemerovskaya oblast&#39;</option>
<option value="43">Kirovskaya oblast&#39;</option>
<option value="44">Kostromskaya oblast&#39;</option>
<option value="45">Kurganskaya oblast&#39;</option>
<option value="46">Kurskaya oblast&#39;</option>
<option value="47">Leningradskaya oblast&#39;</option>
<option value="48">Lipeckaya oblast&#39;</option>
<option value="49">Magadanskaya oblast&#39;</option>
<option value="51">Murmanskaya oblast&#39;</option>
<option value="52">Nizhegorodskaja oblast&#39;</option>
<option value="53">Novgorodskaya oblast&#39;</option>
<option value="54">Novosibirskaya oblast&#39;</option>
<option value="55">Omskaya oblast&#39;</option>
<option value="56">Orenburgskaya oblast&#39;</option>
<option value="57">Orlovskaya oblast&#39;</option>
<option value="58">Penzenskaya oblast&#39;</option>
<option value="60">Pskovskaya oblast&#39;</option>
<option value="61">Rostovskaya oblast&#39;</option>
<option value="62">Rjazanskaya oblast&#39;</option>
<option value="63">Samarskaya oblast&#39;</option>
<option value="64">Saratovskaya oblast&#39;</option>
<option value="65">Sakhalinskaya oblast&#39;</option>
<option value="66">Sverdlovskaya oblast&#39;</option>
<option value="67" selected="selected">Smolenskaya oblast&#39;</option>
<option value="68">Tambovskaya oblast&#39;</option>
<option value="69">Tverskaya oblast&#39;</option>
<option value="70">Tomskaya oblast&#39;</option>
<option value="71">Tul&#39;skaya oblast&#39;</option>
<option value="72">Tyumenskaya oblast&#39;</option>
<option value="73">Ul&#39;ianovskaya oblast&#39;</option>
<option value="74">Chelyabinskaya oblast&#39;</option>
<option value="76">Yaroslavskaya oblast&#39;</option>
<option value="79">Evreyskaya avtonomnaja oblast&#39;</option>
<option value="83">Neneckiy autonomnyy okrug</option>
<option value="86">Khanty-Mansiyskiy avtonomnyy okrug - Yugra</option>
<option value="87">Chukotskiy avtonomnyy okrug</option>
<option value="89">Yamalo-Neneckiy avtonomnyy okrug</option>
</select>'''
        self.assertHTMLEqual(f.render('region', '67'), out)
