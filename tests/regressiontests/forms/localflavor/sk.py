# -*- coding: utf-8 -*-
# Tests for the contrib/localflavor/ SK form fields.

tests = r"""
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
"""
