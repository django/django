# -*- coding: utf-8 -*-

from datetime import date

from django.contrib.localflavor.si.forms import (SIEMSOField, SITaxNumberField,
    SIPhoneNumberField, SIPostalCodeField, SIPostalCodeSelect)
from django.test import SimpleTestCase


class SILocalFlavorTests(SimpleTestCase):
    def test_SITaxNumberField(self):
        error_invalid = [u'Enter a valid tax number in form SIXXXXXXXX']
        valid = {
            '15012557': '15012557',
            'SI15012557': '15012557',
            '22111310': '22111310',
        }
        invalid = {
            '22241310': error_invalid,
            '15012558': error_invalid,
            '1501': error_invalid,
            '1501123123123': error_invalid,
            'abcdabcd': error_invalid,
            '01234579': error_invalid,
        }
        self.assertFieldOutput(SITaxNumberField, valid, invalid)

    def test_SIEMSOField(self):
        error_invalid = [u'This field should contain exactly 13 digits.']
        error_invalid_date = [u'The first 7 digits of the EMSO must represent a valid past date.']
        error_invalid_chksum = [u'The EMSO is not valid.']
        valid = {
            '0205951500462': '0205951500462',
            '2309002500068': '2309002500068',
            '1010985500400': '1010985500400',
        }
        invalid = {
            '0205951500463': error_invalid_chksum,
            '020': error_invalid,
            '020020595150046020595150046': error_invalid,
            'aaaabbbbccccd': error_invalid,
            '1010985500800': error_invalid_chksum,
            '2020095500070': error_invalid_date,
            '5050095500078': error_invalid_date,
            '1010889500408': error_invalid_date,
        }
        self.assertFieldOutput(SIEMSOField, valid, invalid)

    def test_SIEMSOField_info_dict(self):
        valid = {
            '0205951500462': {'nationality': 50, 'gender': 'male', 'birthdate': date(1951, 5, 2)},
            '2309002504063': {'nationality': 50, 'gender': 'male', 'birthdate': date(2002, 9, 23)},
            '1010985505402': {'nationality': 50, 'gender': 'female', 'birthdate': date(1985, 10, 10)},
        }
        for input, info in valid.items():
            f = SIEMSOField()
            f.clean(input)
            self.assertEqual(f.info, info)

    def test_SIPhoneNumberField(self):
        error_invalid = [u'Enter phone number in form +386XXXXXXXX or 0XXXXXXXX.']
        valid = {
            '+38640999999': '40999999',
            '+3861999999': '1999999',
            '0038640999999': '40999999',
            '040999999': '40999999',
            '01999999': '1999999',
            '059099999': '59099999',
            '059 09 99 99': '59099999',
            '0590/999-99': '59099999',
        }
        invalid = {
            '03861999999': error_invalid,
            '3861999999': error_invalid,
        }
        self.assertFieldOutput(SIPhoneNumberField, valid, invalid)

    def test_SIPostalCodeField(self):
        valid = {
            '4000': '4000',
            '1000': '1000'
        }
        invalid = {
            '1113': [u'Select a valid choice. 1113 is not one of the available choices.'],
            '111': [u'Select a valid choice. 111 is not one of the available choices.'],
        }
        self.assertFieldOutput(SIPostalCodeField, valid, invalid)

    def test_SIPostalCodeSelect(self):
        f = SIPostalCodeSelect()
        out = u'''<select name="Kranj">
<option value="8341">Adle\u0161i\u010di</option>
<option value="5270">Ajdov\u0161\u010dina</option>
<option value="6280">Ankaran - Ancarano</option>
<option value="9253">Apa\u010de</option>
<option value="8253">Arti\u010de</option>
<option value="4275">Begunje na Gorenjskem</option>
<option value="1382">Begunje pri Cerknici</option>
<option value="9231">Beltinci</option>
<option value="2234">Benedikt</option>
<option value="2345">Bistrica ob Dravi</option>
<option value="3256">Bistrica ob Sotli</option>
<option value="8259">Bizeljsko</option>
<option value="1223">Blagovica</option>
<option value="8283">Blanca</option>
<option value="4260">Bled</option>
<option value="4273">Blejska Dobrava</option>
<option value="9265">Bodonci</option>
<option value="9222">Bogojina</option>
<option value="4263">Bohinjska Bela</option>
<option value="4264">Bohinjska Bistrica</option>
<option value="4265">Bohinjsko jezero</option>
<option value="1353">Borovnica</option>
<option value="5230">Bovec</option>
<option value="8294">Bo\u0161tanj</option>
<option value="5295">Branik</option>
<option value="3314">Braslov\u010de</option>
<option value="5223">Breginj</option>
<option value="8280">Brestanica</option>
<option value="2354">Bresternica</option>
<option value="4243">Brezje</option>
<option value="1351">Brezovica pri Ljubljani</option>
<option value="8250">Bre\u017eice</option>
<option value="4210">Brnik - aerodrom</option>
<option value="8321">Brusnice</option>
<option value="3255">Bu\u010de</option>
<option value="8276">Bu\u010dka</option>
<option value="9261">Cankova</option>
<option value="3000">Celje</option>
<option value="4207">Cerklje na Gorenjskem</option>
<option value="8263">Cerklje ob Krki</option>
<option value="1380">Cerknica</option>
<option value="5282">Cerkno</option>
<option value="2236">Cerkvenjak</option>
<option value="2215">Cer\u0161ak</option>
<option value="2326">Cirkovce</option>
<option value="2282">Cirkulane</option>
<option value="5273">Col</option>
<option value="6271">Dekani</option>
<option value="5210">Deskle</option>
<option value="2253">Destrnik</option>
<option value="6215">Diva\u010da</option>
<option value="1233">Dob</option>
<option value="3224">Dobje pri Planini</option>
<option value="8257">Dobova</option>
<option value="1423">Dobovec</option>
<option value="5263">Dobravlje</option>
<option value="3204">Dobrna</option>
<option value="8211">Dobrni\u010d</option>
<option value="1356">Dobrova</option>
<option value="9223">Dobrovnik - Dobronak</option>
<option value="5212">Dobrovo v Brdih</option>
<option value="1431">Dol pri Hrastniku</option>
<option value="1262">Dol pri Ljubljani</option>
<option value="1273">Dole pri Litiji</option>
<option value="1331">Dolenja vas</option>
<option value="8350">Dolenjske Toplice</option>
<option value="1230">Dom\u017eale</option>
<option value="2252">Dornava</option>
<option value="5294">Dornberk</option>
<option value="1319">Draga</option>
<option value="8343">Dragatu\u0161</option>
<option value="3222">Dramlje</option>
<option value="2370">Dravograd</option>
<option value="4203">Duplje</option>
<option value="6221">Dutovlje</option>
<option value="8361">Dvor</option>
<option value="2343">Fala</option>
<option value="9208">Fokovci</option>
<option value="2313">Fram</option>
<option value="3213">Frankolovo</option>
<option value="1274">Gabrovka</option>
<option value="8254">Globoko</option>
<option value="5275">Godovi\u010d</option>
<option value="4204">Golnik</option>
<option value="3303">Gomilsko</option>
<option value="4224">Gorenja vas</option>
<option value="3263">Gorica pri Slivnici</option>
<option value="2272">Gori\u0161nica</option>
<option value="9250">Gornja Radgona</option>
<option value="3342">Gornji Grad</option>
<option value="4282">Gozd Martuljek</option>
<option value="9264">Grad</option>
<option value="8332">Gradac</option>
<option value="1384">Grahovo</option>
<option value="5242">Grahovo ob Ba\u010di</option>
<option value="6272">Gra\u010di\u0161\u010de</option>
<option value="5251">Grgar</option>
<option value="3302">Gri\u017ee</option>
<option value="3231">Grobelno</option>
<option value="1290">Grosuplje</option>
<option value="2288">Hajdina</option>
<option value="8362">Hinje</option>
<option value="9205">Hodo\u0161 - Hodos</option>
<option value="1354">Horjul</option>
<option value="1372">Hotedr\u0161ica</option>
<option value="2311">Ho\u010de</option>
<option value="1430">Hrastnik</option>
<option value="6225">Hru\u0161evje</option>
<option value="4276">Hru\u0161ica</option>
<option value="5280">Idrija</option>
<option value="1292">Ig</option>
<option value="6250">Ilirska Bistrica</option>
<option value="6251">Ilirska Bistrica - Trnovo</option>
<option value="2259">Ivanjkovci</option>
<option value="1295">Ivan\u010dna Gorica</option>
<option value="1411">Izlake</option>
<option value="6310">Izola - Isola</option>
<option value="2222">Jakobski Dol</option>
<option value="2221">Jarenina</option>
<option value="6254">Jel\u0161ane</option>
<option value="4270">Jesenice</option>
<option value="8261">Jesenice na Dolenjskem</option>
<option value="3273">Jurklo\u0161ter</option>
<option value="2223">Jurovski Dol</option>
<option value="2256">Jur\u0161inci</option>
<option value="5214">Kal nad Kanalom</option>
<option value="3233">Kalobje</option>
<option value="4246">Kamna Gorica</option>
<option value="2351">Kamnica</option>
<option value="1241">Kamnik</option>
<option value="5213">Kanal</option>
<option value="8258">Kapele</option>
<option value="2362">Kapla</option>
<option value="2325">Kidri\u010devo</option>
<option value="1412">Kisovec</option>
<option value="6253">Kne\u017eak</option>
<option value="5222">Kobarid</option>
<option value="9227">Kobilje</option>
<option value="2276">Kog</option>
<option value="5211">Kojsko</option>
<option value="6223">Komen</option>
<option value="1218">Komenda</option>
<option value="6000">Koper</option>
<option value="8282">Koprivnica</option>
<option value="5296">Kostanjevica na Krasu</option>
<option value="8311">Kostanjevica na Krki</option>
<option value="1336">Kostel</option>
<option value="2394">Kotlje</option>
<option value="6240">Kozina</option>
<option value="3260">Kozje</option>
<option value="1330">Ko\u010devje</option>
<option value="1338">Ko\u010devska Reka</option>
<option value="6256">Ko\u0161ana</option>
<option value="4000" selected="selected">Kranj</option>
<option value="4280">Kranjska Gora</option>
<option value="1281">Kresnice</option>
<option value="4294">Kri\u017ee</option>
<option value="9206">Kri\u017eevci</option>
<option value="9242">Kri\u017eevci pri Ljutomeru</option>
<option value="1301">Krka</option>
<option value="8296">Krmelj</option>
<option value="4245">Kropa</option>
<option value="8262">Kr\u0161ka vas</option>
<option value="8270">Kr\u0161ko</option>
<option value="9263">Kuzma</option>
<option value="2318">Laporje</option>
<option value="1219">Laze v Tuhinju</option>
<option value="3270">La\u0161ko</option>
<option value="2230">Lenart v Slovenskih goricah</option>
<option value="9220">Lendava - Lendva</option>
<option value="4248">Lesce</option>
<option value="3261">Lesi\u010dno</option>
<option value="8273">Leskovec pri Kr\u0161kem</option>
<option value="2372">Libeli\u010de</option>
<option value="2341">Limbu\u0161</option>
<option value="1270">Litija</option>
<option value="3202">Ljube\u010dna</option>
<option value="1000">Ljubljana</option>
<option value="3333">Ljubno ob Savinji</option>
<option value="9240">Ljutomer</option>
<option value="5231">Log pod Mangartom</option>
<option value="1358">Log pri Brezovici</option>
<option value="1370">Logatec</option>
<option value="1434">Loka pri Zidanem Mostu</option>
<option value="3223">Loka pri \u017dusmu</option>
<option value="6219">Lokev</option>
<option value="2324">Lovrenc na Dravskem polju</option>
<option value="2344">Lovrenc na Pohorju</option>
<option value="3215">Lo\u010de</option>
<option value="1318">Lo\u0161ki Potok</option>
<option value="1225">Lukovica</option>
<option value="3334">Lu\u010de</option>
<option value="2322">Maj\u0161perk</option>
<option value="2321">Makole</option>
<option value="9243">Mala Nedelja</option>
<option value="2229">Male\u010dnik</option>
<option value="6273">Marezige</option>
<option value="2000">Maribor</option>
<option value="2206">Marjeta na Dravskem polju</option>
<option value="2281">Markovci</option>
<option value="9221">Martjanci</option>
<option value="6242">Materija</option>
<option value="4211">Mav\u010di\u010de</option>
<option value="9202">Ma\u010dkovci</option>
<option value="1215">Medvode</option>
<option value="1234">Menge\u0161</option>
<option value="8330">Metlika</option>
<option value="2392">Me\u017eica</option>
<option value="2204">Miklav\u017e na Dravskem polju</option>
<option value="2275">Miklav\u017e pri Ormo\u017eu</option>
<option value="5291">Miren</option>
<option value="8233">Mirna</option>
<option value="8216">Mirna Pe\u010d</option>
<option value="2382">Mislinja</option>
<option value="4281">Mojstrana</option>
<option value="8230">Mokronog</option>
<option value="9226">Moravske Toplice</option>
<option value="1251">Morav\u010de</option>
<option value="5216">Most na So\u010di</option>
<option value="1221">Motnik</option>
<option value="3330">Mozirje</option>
<option value="9000">Murska Sobota</option>
<option value="2366">Muta</option>
<option value="4202">Naklo</option>
<option value="3331">Nazarje</option>
<option value="1357">Notranje Gorice</option>
<option value="3203">Nova Cerkev</option>
<option value="5000">Nova Gorica</option>
<option value="1385">Nova vas</option>
<option value="8000">Novo mesto</option>
<option value="6243">Obrov</option>
<option value="9233">Odranci</option>
<option value="2317">Oplotnica</option>
<option value="2312">Orehova vas</option>
<option value="2270">Ormo\u017e</option>
<option value="1316">Ortnek</option>
<option value="1337">Osilnica</option>
<option value="8222">Oto\u010dec</option>
<option value="2361">O\u017ebalt</option>
<option value="2231">Pernica</option>
<option value="2211">Pesnica pri Mariboru</option>
<option value="9203">Petrovci</option>
<option value="3301">Petrov\u010de</option>
<option value="6330">Piran - Pirano</option>
<option value="6257">Pivka</option>
<option value="8255">Pi\u0161ece</option>
<option value="6232">Planina</option>
<option value="3225">Planina pri Sevnici</option>
<option value="6276">Pobegi</option>
<option value="8312">Podbo\u010dje</option>
<option value="5243">Podbrdo</option>
<option value="2273">Podgorci</option>
<option value="6216">Podgorje</option>
<option value="2381">Podgorje pri Slovenj Gradcu</option>
<option value="6244">Podgrad</option>
<option value="1414">Podkum</option>
<option value="2286">Podlehnik</option>
<option value="5272">Podnanos</option>
<option value="4244">Podnart</option>
<option value="3241">Podplat</option>
<option value="3257">Podsreda</option>
<option value="2363">Podvelka</option>
<option value="3254">Pod\u010detrtek</option>
<option value="2208">Pohorje</option>
<option value="2257">Polen\u0161ak</option>
<option value="1355">Polhov Gradec</option>
<option value="4223">Poljane nad \u0160kofjo Loko</option>
<option value="2319">Polj\u010dane</option>
<option value="3313">Polzela</option>
<option value="1272">Pol\u0161nik</option>
<option value="3232">Ponikva</option>
<option value="6320">Portoro\u017e - Portorose</option>
<option value="6230">Postojna</option>
<option value="2331">Pragersko</option>
<option value="3312">Prebold</option>
<option value="4205">Preddvor</option>
<option value="6255">Prem</option>
<option value="1352">Preserje</option>
<option value="6258">Prestranek</option>
<option value="2391">Prevalje</option>
<option value="3262">Prevorje</option>
<option value="1276">Primskovo</option>
<option value="3253">Pristava pri Mestinju</option>
<option value="9207">Prosenjakovci - Partosfalva</option>
<option value="5297">Prva\u010dina</option>
<option value="2250">Ptuj</option>
<option value="2323">Ptujska Gora</option>
<option value="9201">Puconci</option>
<option value="9252">Radenci</option>
<option value="1433">Rade\u010de</option>
<option value="2360">Radlje ob Dravi</option>
<option value="1235">Radomlje</option>
<option value="4240">Radovljica</option>
<option value="8274">Raka</option>
<option value="1381">Rakek</option>
<option value="4283">Rate\u010de - Planica</option>
<option value="2390">Ravne na Koro\u0161kem</option>
<option value="2327">Ra\u010de</option>
<option value="5292">Ren\u010de</option>
<option value="3332">Re\u010dica ob Savinji</option>
<option value="1310">Ribnica</option>
<option value="2364">Ribnica na Pohorju</option>
<option value="3272">Rimske Toplice</option>
<option value="1314">Rob</option>
<option value="3252">Rogatec</option>
<option value="3250">Roga\u0161ka Slatina</option>
<option value="9262">Roga\u0161ovci</option>
<option value="1373">Rovte</option>
<option value="5215">Ro\u010dinj</option>
<option value="2342">Ru\u0161e</option>
<option value="1282">Sava</option>
<option value="4227">Selca</option>
<option value="2352">Selnica ob Dravi</option>
<option value="8333">Semi\u010d</option>
<option value="8281">Senovo</option>
<option value="6224">Seno\u017ee\u010de</option>
<option value="8290">Sevnica</option>
<option value="6333">Se\u010dovlje - Sicciole</option>
<option value="6210">Se\u017eana</option>
<option value="2214">Sladki vrh</option>
<option value="5283">Slap ob Idrijci</option>
<option value="2380">Slovenj Gradec</option>
<option value="2310">Slovenska Bistrica</option>
<option value="3210">Slovenske Konjice</option>
<option value="1216">Smlednik</option>
<option value="1317">Sodra\u017eica</option>
<option value="5250">Solkan</option>
<option value="3335">Sol\u010dava</option>
<option value="4229">Sorica</option>
<option value="4225">Sovodenj</option>
<option value="5232">So\u010da</option>
<option value="5281">Spodnja Idrija</option>
<option value="2241">Spodnji Duplek</option>
<option value="9245">Spodnji Ivanjci</option>
<option value="2277">Sredi\u0161\u010de ob Dravi</option>
<option value="4267">Srednja vas v Bohinju</option>
<option value="8256">Sromlje</option>
<option value="5224">Srpenica</option>
<option value="1242">Stahovica</option>
<option value="1332">Stara Cerkev</option>
<option value="8342">Stari trg ob Kolpi</option>
<option value="1386">Stari trg pri Lo\u017eu</option>
<option value="2205">Star\u0161e</option>
<option value="2289">Stoperce</option>
<option value="8322">Stopi\u010de</option>
<option value="3206">Stranice</option>
<option value="8351">Stra\u017ea</option>
<option value="1313">Struge</option>
<option value="8293">Studenec</option>
<option value="8331">Suhor</option>
<option value="2353">Sv. Duh na Ostrem Vrhu</option>
<option value="2233">Sveta Ana v Slovenskih goricah</option>
<option value="2235">Sveta Trojica v Slovenskih goricah</option>
<option value="9244">Sveti Jurij ob \u0160\u010davnici</option>
<option value="2258">Sveti Toma\u017e</option>
<option value="3264">Sveti \u0160tefan</option>
<option value="3304">Tabor</option>
<option value="3221">Teharje</option>
<option value="9251">Ti\u0161ina</option>
<option value="5220">Tolmin</option>
<option value="3326">Topol\u0161ica</option>
<option value="2371">Trbonje</option>
<option value="1420">Trbovlje</option>
<option value="8231">Trebelno</option>
<option value="8210">Trebnje</option>
<option value="5252">Trnovo pri Gorici</option>
<option value="2254">Trnovska vas</option>
<option value="1222">Trojane</option>
<option value="1236">Trzin</option>
<option value="4290">Tr\u017ei\u010d</option>
<option value="8295">Tr\u017ei\u0161\u010de</option>
<option value="1311">Turjak</option>
<option value="9224">Turni\u0161\u010de</option>
<option value="8323">Ur\u0161na sela</option>
<option value="1252">Va\u010de</option>
<option value="3320">Velenje - dostava</option>
<option value="3322">Velenje - po\u0161tni predali</option>
<option value="8212">Velika Loka</option>
<option value="2274">Velika Nedelja</option>
<option value="9225">Velika Polana</option>
<option value="1315">Velike La\u0161\u010de</option>
<option value="8213">Veliki Gaber</option>
<option value="9241">Ver\u017eej</option>
<option value="1312">Videm - Dobrepolje</option>
<option value="2284">Videm pri Ptuju</option>
<option value="8344">Vinica pri \u010crnomlju</option>
<option value="5271">Vipava</option>
<option value="4212">Visoko</option>
<option value="3205">Vitanje</option>
<option value="2255">Vitomarci</option>
<option value="1294">Vi\u0161nja Gora</option>
<option value="1217">Vodice</option>
<option value="3212">Vojnik</option>
<option value="2232">Voli\u010dina</option>
<option value="5293">Vol\u010dja Draga</option>
<option value="3305">Vransko</option>
<option value="6217">Vremski Britof</option>
<option value="1360">Vrhnika</option>
<option value="2365">Vuhred</option>
<option value="2367">Vuzenica</option>
<option value="8292">Zabukovje</option>
<option value="1410">Zagorje ob Savi</option>
<option value="1303">Zagradec</option>
<option value="2283">Zavr\u010d</option>
<option value="8272">Zdole</option>
<option value="4201">Zgornja Besnica</option>
<option value="2242">Zgornja Korena</option>
<option value="2201">Zgornja Kungota</option>
<option value="2316">Zgornja Lo\u017enica</option>
<option value="2314">Zgornja Polskava</option>
<option value="2213">Zgornja Velka</option>
<option value="4247">Zgornje Gorje</option>
<option value="4206">Zgornje Jezersko</option>
<option value="2285">Zgornji Leskovec</option>
<option value="1432">Zidani Most</option>
<option value="3214">Zre\u010de</option>
<option value="8251">\u010cate\u017e ob Savi</option>
<option value="1413">\u010cem\u0161enik</option>
<option value="5253">\u010cepovan</option>
<option value="9232">\u010cren\u0161ovci</option>
<option value="2393">\u010crna na Koro\u0161kem</option>
<option value="6275">\u010crni Kal</option>
<option value="5274">\u010crni Vrh nad Idrijo</option>
<option value="5262">\u010crni\u010de</option>
<option value="8340">\u010crnomelj</option>
<option value="9204">\u0160alovci</option>
<option value="5261">\u0160empas</option>
<option value="5290">\u0160empeter pri Gorici</option>
<option value="3311">\u0160empeter v Savinjski dolini</option>
<option value="2212">\u0160entilj v Slovenskih goricah</option>
<option value="8297">\u0160entjan\u017e</option>
<option value="2373">\u0160entjan\u017e pri Dravogradu</option>
<option value="8310">\u0160entjernej</option>
<option value="3230">\u0160entjur</option>
<option value="3271">\u0160entrupert</option>
<option value="8232">\u0160entrupert</option>
<option value="1296">\u0160entvid pri Sti\u010dni</option>
<option value="4208">\u0160en\u010dur</option>
<option value="8275">\u0160kocjan</option>
<option value="6281">\u0160kofije</option>
<option value="4220">\u0160kofja Loka</option>
<option value="3211">\u0160kofja vas</option>
<option value="1291">\u0160kofljica</option>
<option value="6274">\u0160marje</option>
<option value="1293">\u0160marje - Sap</option>
<option value="3240">\u0160marje pri Jel\u0161ah</option>
<option value="8220">\u0160marje\u0161ke Toplice</option>
<option value="2315">\u0160martno na Pohorju</option>
<option value="3341">\u0160martno ob Dreti</option>
<option value="3327">\u0160martno ob Paki</option>
<option value="1275">\u0160martno pri Litiji</option>
<option value="2383">\u0160martno pri Slovenj Gradcu</option>
<option value="3201">\u0160martno v Ro\u017eni dolini</option>
<option value="3325">\u0160o\u0161tanj</option>
<option value="6222">\u0160tanjel</option>
<option value="3220">\u0160tore</option>
<option value="4209">\u017dabnica</option>
<option value="3310">\u017dalec</option>
<option value="4228">\u017delezniki</option>
<option value="2287">\u017detale</option>
<option value="4226">\u017diri</option>
<option value="4274">\u017dirovnica</option>
<option value="8360">\u017du\u017eemberk</option>
</select>'''
        self.assertHTMLEqual(f.render('Kranj', '4000'), out)
