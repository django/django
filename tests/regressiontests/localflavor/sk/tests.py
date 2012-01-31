from django.contrib.localflavor.sk.forms import (SKRegionSelect,
    SKPostalCodeField, SKDistrictSelect)

from django.test import SimpleTestCase


class SKLocalFlavorTests(SimpleTestCase):
    def test_SKRegionSelect(self):
        f = SKRegionSelect()
        out = u'''<select name="regions">
<option value="BB">Banska Bystrica region</option>
<option value="BA">Bratislava region</option>
<option value="KE">Kosice region</option>
<option value="NR">Nitra region</option>
<option value="PO">Presov region</option>
<option value="TN">Trencin region</option>
<option value="TT" selected="selected">Trnava region</option>
<option value="ZA">Zilina region</option>
</select>'''
        self.assertHTMLEqual(f.render('regions', 'TT'), out)

    def test_SKDistrictSelect(self):
        f = SKDistrictSelect()
        out = u'''<select name="Districts">
<option value="BB">Banska Bystrica</option>
<option value="BS">Banska Stiavnica</option>
<option value="BJ">Bardejov</option>
<option value="BN">Banovce nad Bebravou</option>
<option value="BR">Brezno</option>
<option value="BA1">Bratislava I</option>
<option value="BA2">Bratislava II</option>
<option value="BA3">Bratislava III</option>
<option value="BA4">Bratislava IV</option>
<option value="BA5">Bratislava V</option>
<option value="BY">Bytca</option>
<option value="CA">Cadca</option>
<option value="DT">Detva</option>
<option value="DK">Dolny Kubin</option>
<option value="DS">Dunajska Streda</option>
<option value="GA">Galanta</option>
<option value="GL">Gelnica</option>
<option value="HC">Hlohovec</option>
<option value="HE">Humenne</option>
<option value="IL">Ilava</option>
<option value="KK">Kezmarok</option>
<option value="KN">Komarno</option>
<option value="KE1">Kosice I</option>
<option value="KE2">Kosice II</option>
<option value="KE3">Kosice III</option>
<option value="KE4">Kosice IV</option>
<option value="KEO">Kosice - okolie</option>
<option value="KA">Krupina</option>
<option value="KM">Kysucke Nove Mesto</option>
<option value="LV">Levice</option>
<option value="LE">Levoca</option>
<option value="LM">Liptovsky Mikulas</option>
<option value="LC">Lucenec</option>
<option value="MA">Malacky</option>
<option value="MT">Martin</option>
<option value="ML">Medzilaborce</option>
<option value="MI">Michalovce</option>
<option value="MY">Myjava</option>
<option value="NO">Namestovo</option>
<option value="NR">Nitra</option>
<option value="NM">Nove Mesto nad Vahom</option>
<option value="NZ">Nove Zamky</option>
<option value="PE">Partizanske</option>
<option value="PK">Pezinok</option>
<option value="PN">Piestany</option>
<option value="PT">Poltar</option>
<option value="PP">Poprad</option>
<option value="PB">Povazska Bystrica</option>
<option value="PO">Presov</option>
<option value="PD">Prievidza</option>
<option value="PU">Puchov</option>
<option value="RA">Revuca</option>
<option value="RS">Rimavska Sobota</option>
<option value="RV">Roznava</option>
<option value="RK" selected="selected">Ruzomberok</option>
<option value="SB">Sabinov</option>
<option value="SC">Senec</option>
<option value="SE">Senica</option>
<option value="SI">Skalica</option>
<option value="SV">Snina</option>
<option value="SO">Sobrance</option>
<option value="SN">Spisska Nova Ves</option>
<option value="SL">Stara Lubovna</option>
<option value="SP">Stropkov</option>
<option value="SK">Svidnik</option>
<option value="SA">Sala</option>
<option value="TO">Topolcany</option>
<option value="TV">Trebisov</option>
<option value="TN">Trencin</option>
<option value="TT">Trnava</option>
<option value="TR">Turcianske Teplice</option>
<option value="TS">Tvrdosin</option>
<option value="VK">Velky Krtis</option>
<option value="VT">Vranov nad Toplou</option>
<option value="ZM">Zlate Moravce</option>
<option value="ZV">Zvolen</option>
<option value="ZC">Zarnovica</option>
<option value="ZH">Ziar nad Hronom</option>
<option value="ZA">Zilina</option>
</select>'''
        self.assertHTMLEqual(f.render('Districts', 'RK'), out)

    def test_SKPostalCodeField(self):
        error_format = [u'Enter a postal code in the format XXXXX or XXX XX.']
        valid = {
            '91909': '91909',
            '917 01': '91701',
        }
        invalid = {
            '84545x': error_format,
        }
        self.assertFieldOutput(SKPostalCodeField, valid, invalid)
