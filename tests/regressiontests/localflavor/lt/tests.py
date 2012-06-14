# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.test import SimpleTestCase

from django.contrib.localflavor.lt.forms import LTIDCodeField, \
                                                LTMunicipalitySelect, \
                                                LTCountySelect

class LTLocalFlavorTests(SimpleTestCase):

    def test_LTIDCodeField(self):
        error_len = ['ID Code consists of exactly 11 decimal digits.']
        error_check = ['Wrong ID Code checksum.']

        valid = {
            '33309240064': '33309240064',
            '35002125431': '35002125431',
            '61205010081': '61205010081',
            '48504140959': '48504140959',
        }

        invalid = {
            '3456': error_len,
            '123456789101': error_len,
            '33309240065': error_check,
            'hello': error_len,
            '134535443i2': error_len,
            '48504140956': error_check,
            '48504140953': error_check
        }

        self.assertFieldOutput(LTIDCodeField, valid, invalid)

    def test_LTCountySelect(self):
        f = LTCountySelect()
        expected = """
            <select name="test">
            <option value="alytus">Alytus</option>
            <option value="kaunas">Kaunas</option>
            <option value="klaipeda">Klaipėda</option>
            <option value="mariampole">Mariampolė</option>
            <option value="panevezys">Panevėžys</option>
            <option value="siauliai">Šiauliai</option>
            <option value="taurage">Tauragė</option>
            <option value="telsiai">Telšiai</option>
            <option value="utena">Utena</option>
            <option value="vilnius">Vilnius</option>
            </select>
        """
        self.assertHTMLEqual(f.render('test', None), expected)

    def test_LTMunicipalitySelect(self):
        f = LTMunicipalitySelect()
        expected = """
            <select name="test">
            <option value="akmene">Akmenė district</option>
            <option value="alytus_c">Alytus city</option>
            <option value="alytus">Alytus district</option>
            <option value="anyksciai">Anykščiai district</option>
            <option value="birstonas">Birštonas</option>
            <option value="birzai">Biržai district</option>
            <option value="druskininkai">Druskininkai</option>
            <option value="elektrenai">Elektrėnai</option>
            <option value="ignalina">Ignalina district</option>
            <option value="jonava">Jonava district</option>
            <option value="joniskis">Joniškis district</option>
            <option value="jurbarkas">Jurbarkas district</option>
            <option value="kaisiadorys">Kaišiadorys district</option>
            <option value="kalvarija">Kalvarija</option>
            <option value="kaunas_c">Kaunas city</option>
            <option value="kaunas">Kaunas district</option>
            <option value="kazluruda">Kazlų Rūda</option>
            <option value="kedainiai">Kėdainiai district</option>
            <option value="kelme">Kelmė district</option>
            <option value="klaipeda_c">Klaipėda city</option>
            <option value="klaipeda">Klaipėda district</option>
            <option value="kretinga">Kretinga district</option>
            <option value="kupiskis">Kupiškis district</option>
            <option value="lazdijai">Lazdijai district</option>
            <option value="marijampole">Marijampolė</option>
            <option value="mazeikiai">Mažeikiai district</option>
            <option value="moletai">Molėtai district</option>
            <option value="neringa">Neringa</option>
            <option value="pagegiai">Pagėgiai</option>
            <option value="pakruojis">Pakruojis district</option>
            <option value="palanga">Palanga city</option>
            <option value="panevezys_c">Panevėžys city</option>
            <option value="panevezys">Panevėžys district</option>
            <option value="pasvalys">Pasvalys district</option>
            <option value="plunge">Plungė district</option>
            <option value="prienai">Prienai district</option>
            <option value="radviliskis">Radviliškis district</option>
            <option value="raseiniai">Raseiniai district</option>
            <option value="rietavas">Rietavas</option>
            <option value="rokiskis">Rokiškis district</option>
            <option value="skuodas">Skuodas district</option>
            <option value="sakiai">Šakiai district</option>
            <option value="salcininkai">Šalčininkai district</option>
            <option value="siauliai_c">Šiauliai city</option>
            <option value="siauliai">Šiauliai district</option>
            <option value="silale">Šilalė district</option>
            <option value="silute">Šilutė district</option>
            <option value="sirvintos">Širvintos district</option>
            <option value="svencionys">Švenčionys district</option>
            <option value="taurage">Tauragė district</option>
            <option value="telsiai">Telšiai district</option>
            <option value="trakai">Trakai district</option>
            <option value="ukmerge">Ukmergė district</option>
            <option value="utena">Utena district</option>
            <option value="varena">Varėna district</option>
            <option value="vilkaviskis">Vilkaviškis district</option>
            <option value="vilnius_c">Vilnius city</option>
            <option value="vilnius">Vilnius district</option>
            <option value="visaginas">Visaginas</option>
            <option value="zarasai">Zarasai district</option>
            </select>
        """
        self.assertHTMLEqual(f.render('test', None), expected)
