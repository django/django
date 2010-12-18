from django.contrib.localflavor.pl.forms import (PLProvinceSelect,
    PLCountySelect, PLPostalCodeField, PLNIPField, PLPESELField, PLREGONField)

from utils import LocalFlavorTestCase


class PLLocalFlavorTests(LocalFlavorTestCase):
    def test_PLProvinceSelect(self):
        f = PLProvinceSelect()
        out = u'''<select name="voivodeships">
<option value="lower_silesia">Lower Silesia</option>
<option value="kuyavia-pomerania">Kuyavia-Pomerania</option>
<option value="lublin">Lublin</option>
<option value="lubusz">Lubusz</option>
<option value="lodz">Lodz</option>
<option value="lesser_poland">Lesser Poland</option>
<option value="masovia">Masovia</option>
<option value="opole">Opole</option>
<option value="subcarpatia">Subcarpatia</option>
<option value="podlasie">Podlasie</option>
<option value="pomerania" selected="selected">Pomerania</option>
<option value="silesia">Silesia</option>
<option value="swietokrzyskie">Swietokrzyskie</option>
<option value="warmia-masuria">Warmia-Masuria</option>
<option value="greater_poland">Greater Poland</option>
<option value="west_pomerania">West Pomerania</option>
</select>'''
        self.assertEqual(f.render('voivodeships', 'pomerania'), out)
    
    def test_PLCountrySelect(self):
        f = PLCountySelect()
        out = u'''<select name="administrativeunit">
<option value="wroclaw">Wroc\u0142aw</option>
<option value="jeleniagora">Jelenia G\xf3ra</option>
<option value="legnica">Legnica</option>
<option value="boleslawiecki">boles\u0142awiecki</option>
<option value="dzierzoniowski">dzier\u017coniowski</option>
<option value="glogowski">g\u0142ogowski</option>
<option value="gorowski">g\xf3rowski</option>
<option value="jaworski">jaworski</option>
<option value="jeleniogorski">jeleniog\xf3rski</option>
<option value="kamiennogorski">kamiennog\xf3rski</option>
<option value="klodzki">k\u0142odzki</option>
<option value="legnicki">legnicki</option>
<option value="lubanski">luba\u0144ski</option>
<option value="lubinski">lubi\u0144ski</option>
<option value="lwowecki">lw\xf3wecki</option>
<option value="milicki">milicki</option>
<option value="olesnicki">ole\u015bnicki</option>
<option value="olawski">o\u0142awski</option>
<option value="polkowicki">polkowicki</option>
<option value="strzelinski">strzeli\u0144ski</option>
<option value="sredzki">\u015bredzki</option>
<option value="swidnicki">\u015bwidnicki</option>
<option value="trzebnicki">trzebnicki</option>
<option value="walbrzyski">wa\u0142brzyski</option>
<option value="wolowski">wo\u0142owski</option>
<option value="wroclawski">wroc\u0142awski</option>
<option value="zabkowicki">z\u0105bkowicki</option>
<option value="zgorzelecki">zgorzelecki</option>
<option value="zlotoryjski">z\u0142otoryjski</option>
<option value="bydgoszcz">Bydgoszcz</option>
<option value="torun">Toru\u0144</option>
<option value="wloclawek">W\u0142oc\u0142awek</option>
<option value="grudziadz">Grudzi\u0105dz</option>
<option value="aleksandrowski">aleksandrowski</option>
<option value="brodnicki">brodnicki</option>
<option value="bydgoski">bydgoski</option>
<option value="chelminski">che\u0142mi\u0144ski</option>
<option value="golubsko-dobrzynski">golubsko-dobrzy\u0144ski</option>
<option value="grudziadzki">grudzi\u0105dzki</option>
<option value="inowroclawski">inowroc\u0142awski</option>
<option value="lipnowski">lipnowski</option>
<option value="mogilenski">mogile\u0144ski</option>
<option value="nakielski">nakielski</option>
<option value="radziejowski">radziejowski</option>
<option value="rypinski">rypi\u0144ski</option>
<option value="sepolenski">s\u0119pole\u0144ski</option>
<option value="swiecki">\u015bwiecki</option>
<option value="torunski">toru\u0144ski</option>
<option value="tucholski">tucholski</option>
<option value="wabrzeski">w\u0105brzeski</option>
<option value="wloclawski">wroc\u0142awski</option>
<option value="zninski">\u017ani\u0144ski</option>
<option value="lublin">Lublin</option>
<option value="biala-podlaska">Bia\u0142a Podlaska</option>
<option value="chelm">Che\u0142m</option>
<option value="zamosc">Zamo\u015b\u0107</option>
<option value="bialski">bialski</option>
<option value="bilgorajski">bi\u0142gorajski</option>
<option value="chelmski">che\u0142mski</option>
<option value="hrubieszowski">hrubieszowski</option>
<option value="janowski">janowski</option>
<option value="krasnostawski">krasnostawski</option>
<option value="krasnicki">kra\u015bnicki</option>
<option value="lubartowski">lubartowski</option>
<option value="lubelski">lubelski</option>
<option value="leczynski">\u0142\u0119czy\u0144ski</option>
<option value="lukowski">\u0142ukowski</option>
<option value="opolski">opolski</option>
<option value="parczewski">parczewski</option>
<option value="pulawski">pu\u0142awski</option>
<option value="radzynski">radzy\u0144ski</option>
<option value="rycki">rycki</option>
<option value="swidnicki">\u015bwidnicki</option>
<option value="tomaszowski">tomaszowski</option>
<option value="wlodawski">w\u0142odawski</option>
<option value="zamojski">zamojski</option>
<option value="gorzow-wielkopolski">Gorz\xf3w Wielkopolski</option>
<option value="zielona-gora">Zielona G\xf3ra</option>
<option value="gorzowski">gorzowski</option>
<option value="krosnienski">kro\u015bnie\u0144ski</option>
<option value="miedzyrzecki">mi\u0119dzyrzecki</option>
<option value="nowosolski">nowosolski</option>
<option value="slubicki">s\u0142ubicki</option>
<option value="strzelecko-drezdenecki">strzelecko-drezdenecki</option>
<option value="sulecinski">sule\u0144ci\u0144ski</option>
<option value="swiebodzinski">\u015bwiebodzi\u0144ski</option>
<option value="wschowski">wschowski</option>
<option value="zielonogorski">zielonog\xf3rski</option>
<option value="zaganski">\u017caga\u0144ski</option>
<option value="zarski">\u017carski</option>
<option value="lodz">\u0141\xf3d\u017a</option>
<option value="piotrkow-trybunalski">Piotrk\xf3w Trybunalski</option>
<option value="skierniewice">Skierniewice</option>
<option value="belchatowski">be\u0142chatowski</option>
<option value="brzezinski">brzezi\u0144ski</option>
<option value="kutnowski">kutnowski</option>
<option value="laski">\u0142aski</option>
<option value="leczycki">\u0142\u0119czycki</option>
<option value="lowicki">\u0142owicki</option>
<option value="lodzki wschodni">\u0142\xf3dzki wschodni</option>
<option value="opoczynski">opoczy\u0144ski</option>
<option value="pabianicki">pabianicki</option>
<option value="pajeczanski">paj\u0119cza\u0144ski</option>
<option value="piotrkowski">piotrkowski</option>
<option value="poddebicki">podd\u0119bicki</option>
<option value="radomszczanski">radomszcza\u0144ski</option>
<option value="rawski">rawski</option>
<option value="sieradzki">sieradzki</option>
<option value="skierniewicki">skierniewicki</option>
<option value="tomaszowski">tomaszowski</option>
<option value="wielunski">wielu\u0144ski</option>
<option value="wieruszowski">wieruszowski</option>
<option value="zdunskowolski">zdu\u0144skowolski</option>
<option value="zgierski">zgierski</option>
<option value="krakow">Krak\xf3w</option>
<option value="tarnow">Tarn\xf3w</option>
<option value="nowy-sacz">Nowy S\u0105cz</option>
<option value="bochenski">boche\u0144ski</option>
<option value="brzeski">brzeski</option>
<option value="chrzanowski">chrzanowski</option>
<option value="dabrowski">d\u0105browski</option>
<option value="gorlicki">gorlicki</option>
<option value="krakowski">krakowski</option>
<option value="limanowski">limanowski</option>
<option value="miechowski">miechowski</option>
<option value="myslenicki">my\u015blenicki</option>
<option value="nowosadecki">nowos\u0105decki</option>
<option value="nowotarski">nowotarski</option>
<option value="olkuski">olkuski</option>
<option value="oswiecimski">o\u015bwi\u0119cimski</option>
<option value="proszowicki">proszowicki</option>
<option value="suski">suski</option>
<option value="tarnowski">tarnowski</option>
<option value="tatrzanski">tatrza\u0144ski</option>
<option value="wadowicki">wadowicki</option>
<option value="wielicki">wielicki</option>
<option value="warszawa">Warszawa</option>
<option value="ostroleka">Ostro\u0142\u0119ka</option>
<option value="plock">P\u0142ock</option>
<option value="radom">Radom</option>
<option value="siedlce">Siedlce</option>
<option value="bialobrzeski">bia\u0142obrzeski</option>
<option value="ciechanowski">ciechanowski</option>
<option value="garwolinski">garwoli\u0144ski</option>
<option value="gostyninski">gostyni\u0144ski</option>
<option value="grodziski">grodziski</option>
<option value="grojecki">gr\xf3jecki</option>
<option value="kozienicki">kozenicki</option>
<option value="legionowski">legionowski</option>
<option value="lipski">lipski</option>
<option value="losicki">\u0142osicki</option>
<option value="makowski">makowski</option>
<option value="minski">mi\u0144ski</option>
<option value="mlawski">m\u0142awski</option>
<option value="nowodworski">nowodworski</option>
<option value="ostrolecki">ostro\u0142\u0119cki</option>
<option value="ostrowski">ostrowski</option>
<option value="otwocki">otwocki</option>
<option value="piaseczynski">piaseczy\u0144ski</option>
<option value="plocki">p\u0142ocki</option>
<option value="plonski">p\u0142o\u0144ski</option>
<option value="pruszkowski">pruszkowski</option>
<option value="przasnyski">przasnyski</option>
<option value="przysuski">przysuski</option>
<option value="pultuski">pu\u0142tuski</option>
<option value="radomski">radomski</option>
<option value="siedlecki">siedlecki</option>
<option value="sierpecki">sierpecki</option>
<option value="sochaczewski">sochaczewski</option>
<option value="sokolowski">soko\u0142owski</option>
<option value="szydlowiecki">szyd\u0142owiecki</option>
<option value="warszawski-zachodni">warszawski zachodni</option>
<option value="wegrowski">w\u0119growski</option>
<option value="wolominski">wo\u0142omi\u0144ski</option>
<option value="wyszkowski">wyszkowski</option>
<option value="zwolenski">zwole\u0144ski</option>
<option value="zurominski">\u017curomi\u0144ski</option>
<option value="zyrardowski">\u017cyrardowski</option>
<option value="opole">Opole</option>
<option value="brzeski">brzeski</option>
<option value="glubczycki">g\u0142ubczyski</option>
<option value="kedzierzynsko-kozielski">k\u0119dzierzy\u0144ski-kozielski</option>
<option value="kluczborski">kluczborski</option>
<option value="krapkowicki">krapkowicki</option>
<option value="namyslowski">namys\u0142owski</option>
<option value="nyski">nyski</option>
<option value="oleski">oleski</option>
<option value="opolski">opolski</option>
<option value="prudnicki">prudnicki</option>
<option value="strzelecki">strzelecki</option>
<option value="rzeszow">Rzesz\xf3w</option>
<option value="krosno">Krosno</option>
<option value="przemysl">Przemy\u015bl</option>
<option value="tarnobrzeg">Tarnobrzeg</option>
<option value="bieszczadzki">bieszczadzki</option>
<option value="brzozowski">brzozowski</option>
<option value="debicki">d\u0119bicki</option>
<option value="jaroslawski">jaros\u0142awski</option>
<option value="jasielski">jasielski</option>
<option value="kolbuszowski">kolbuszowski</option>
<option value="krosnienski">kro\u015bnie\u0144ski</option>
<option value="leski">leski</option>
<option value="lezajski">le\u017cajski</option>
<option value="lubaczowski">lubaczowski</option>
<option value="lancucki">\u0142a\u0144cucki</option>
<option value="mielecki">mielecki</option>
<option value="nizanski">ni\u017ca\u0144ski</option>
<option value="przemyski">przemyski</option>
<option value="przeworski">przeworski</option>
<option value="ropczycko-sedziszowski">ropczycko-s\u0119dziszowski</option>
<option value="rzeszowski">rzeszowski</option>
<option value="sanocki">sanocki</option>
<option value="stalowowolski">stalowowolski</option>
<option value="strzyzowski">strzy\u017cowski</option>
<option value="tarnobrzeski">tarnobrzeski</option>
<option value="bialystok">Bia\u0142ystok</option>
<option value="lomza">\u0141om\u017ca</option>
<option value="suwalki">Suwa\u0142ki</option>
<option value="augustowski">augustowski</option>
<option value="bialostocki">bia\u0142ostocki</option>
<option value="bielski">bielski</option>
<option value="grajewski">grajewski</option>
<option value="hajnowski">hajnowski</option>
<option value="kolnenski">kolne\u0144ski</option>
<option value="\u0142omzynski">\u0142om\u017cy\u0144ski</option>
<option value="moniecki">moniecki</option>
<option value="sejnenski">sejne\u0144ski</option>
<option value="siemiatycki">siematycki</option>
<option value="sokolski">sok\xf3lski</option>
<option value="suwalski">suwalski</option>
<option value="wysokomazowiecki">wysokomazowiecki</option>
<option value="zambrowski">zambrowski</option>
<option value="gdansk">Gda\u0144sk</option>
<option value="gdynia">Gdynia</option>
<option value="slupsk">S\u0142upsk</option>
<option value="sopot">Sopot</option>
<option value="bytowski">bytowski</option>
<option value="chojnicki">chojnicki</option>
<option value="czluchowski">cz\u0142uchowski</option>
<option value="kartuski">kartuski</option>
<option value="koscierski">ko\u015bcierski</option>
<option value="kwidzynski">kwidzy\u0144ski</option>
<option value="leborski">l\u0119borski</option>
<option value="malborski">malborski</option>
<option value="nowodworski">nowodworski</option>
<option value="gdanski">gda\u0144ski</option>
<option value="pucki">pucki</option>
<option value="slupski">s\u0142upski</option>
<option value="starogardzki">starogardzki</option>
<option value="sztumski">sztumski</option>
<option value="tczewski">tczewski</option>
<option value="wejherowski">wejcherowski</option>
<option value="katowice" selected="selected">Katowice</option>
<option value="bielsko-biala">Bielsko-Bia\u0142a</option>
<option value="bytom">Bytom</option>
<option value="chorzow">Chorz\xf3w</option>
<option value="czestochowa">Cz\u0119stochowa</option>
<option value="dabrowa-gornicza">D\u0105browa G\xf3rnicza</option>
<option value="gliwice">Gliwice</option>
<option value="jastrzebie-zdroj">Jastrz\u0119bie Zdr\xf3j</option>
<option value="jaworzno">Jaworzno</option>
<option value="myslowice">Mys\u0142owice</option>
<option value="piekary-slaskie">Piekary \u015al\u0105skie</option>
<option value="ruda-slaska">Ruda \u015al\u0105ska</option>
<option value="rybnik">Rybnik</option>
<option value="siemianowice-slaskie">Siemianowice \u015al\u0105skie</option>
<option value="sosnowiec">Sosnowiec</option>
<option value="swietochlowice">\u015awi\u0119toch\u0142owice</option>
<option value="tychy">Tychy</option>
<option value="zabrze">Zabrze</option>
<option value="zory">\u017bory</option>
<option value="bedzinski">b\u0119dzi\u0144ski</option>
<option value="bielski">bielski</option>
<option value="bierunsko-ledzinski">bieru\u0144sko-l\u0119dzi\u0144ski</option>
<option value="cieszynski">cieszy\u0144ski</option>
<option value="czestochowski">cz\u0119stochowski</option>
<option value="gliwicki">gliwicki</option>
<option value="klobucki">k\u0142obucki</option>
<option value="lubliniecki">lubliniecki</option>
<option value="mikolowski">miko\u0142owski</option>
<option value="myszkowski">myszkowski</option>
<option value="pszczynski">pszczy\u0144ski</option>
<option value="raciborski">raciborski</option>
<option value="rybnicki">rybnicki</option>
<option value="tarnogorski">tarnog\xf3rski</option>
<option value="wodzislawski">wodzis\u0142awski</option>
<option value="zawiercianski">zawiercia\u0144ski</option>
<option value="zywiecki">\u017cywiecki</option>
<option value="kielce">Kielce</option>
<option value="buski">buski</option>
<option value="jedrzejowski">j\u0119drzejowski</option>
<option value="kazimierski">kazimierski</option>
<option value="kielecki">kielecki</option>
<option value="konecki">konecki</option>
<option value="opatowski">opatowski</option>
<option value="ostrowiecki">ostrowiecki</option>
<option value="pinczowski">pi\u0144czowski</option>
<option value="sandomierski">sandomierski</option>
<option value="skarzyski">skar\u017cyski</option>
<option value="starachowicki">starachowicki</option>
<option value="staszowski">staszowski</option>
<option value="wloszczowski">w\u0142oszczowski</option>
<option value="olsztyn">Olsztyn</option>
<option value="elblag">Elbl\u0105g</option>
<option value="bartoszycki">bartoszycki</option>
<option value="braniewski">braniewski</option>
<option value="dzialdowski">dzia\u0142dowski</option>
<option value="elblaski">elbl\u0105ski</option>
<option value="elcki">e\u0142cki</option>
<option value="gizycki">gi\u017cycki</option>
<option value="goldapski">go\u0142dapski</option>
<option value="ilawski">i\u0142awski</option>
<option value="ketrzynski">k\u0119trzy\u0144ski</option>
<option value="lidzbarski">lidzbarski</option>
<option value="mragowski">mr\u0105gowski</option>
<option value="nidzicki">nidzicki</option>
<option value="nowomiejski">nowomiejski</option>
<option value="olecki">olecki</option>
<option value="olsztynski">olszty\u0144ski</option>
<option value="ostrodzki">ostr\xf3dzki</option>
<option value="piski">piski</option>
<option value="szczycienski">szczycie\u0144ski</option>
<option value="wegorzewski">w\u0119gorzewski</option>
<option value="poznan">Pozna\u0144</option>
<option value="kalisz">Kalisz</option>
<option value="konin">Konin</option>
<option value="leszno">Leszno</option>
<option value="chodzieski">chodziejski</option>
<option value="czarnkowsko-trzcianecki">czarnkowsko-trzcianecki</option>
<option value="gnieznienski">gnie\u017anie\u0144ski</option>
<option value="gostynski">gosty\u0144ski</option>
<option value="grodziski">grodziski</option>
<option value="jarocinski">jaroci\u0144ski</option>
<option value="kaliski">kaliski</option>
<option value="kepinski">k\u0119pi\u0144ski</option>
<option value="kolski">kolski</option>
<option value="koninski">koni\u0144ski</option>
<option value="koscianski">ko\u015bcia\u0144ski</option>
<option value="krotoszynski">krotoszy\u0144ski</option>
<option value="leszczynski">leszczy\u0144ski</option>
<option value="miedzychodzki">mi\u0119dzychodzki</option>
<option value="nowotomyski">nowotomyski</option>
<option value="obornicki">obornicki</option>
<option value="ostrowski">ostrowski</option>
<option value="ostrzeszowski">ostrzeszowski</option>
<option value="pilski">pilski</option>
<option value="pleszewski">pleszewski</option>
<option value="poznanski">pozna\u0144ski</option>
<option value="rawicki">rawicki</option>
<option value="slupecki">s\u0142upecki</option>
<option value="szamotulski">szamotulski</option>
<option value="sredzki">\u015bredzki</option>
<option value="sremski">\u015bremski</option>
<option value="turecki">turecki</option>
<option value="wagrowiecki">w\u0105growiecki</option>
<option value="wolsztynski">wolszty\u0144ski</option>
<option value="wrzesinski">wrzesi\u0144ski</option>
<option value="zlotowski">z\u0142otowski</option>
<option value="bialogardzki">bia\u0142ogardzki</option>
<option value="choszczenski">choszcze\u0144ski</option>
<option value="drawski">drawski</option>
<option value="goleniowski">goleniowski</option>
<option value="gryficki">gryficki</option>
<option value="gryfinski">gryfi\u0144ski</option>
<option value="kamienski">kamie\u0144ski</option>
<option value="kolobrzeski">ko\u0142obrzeski</option>
<option value="koszalinski">koszali\u0144ski</option>
<option value="lobeski">\u0142obeski</option>
<option value="mysliborski">my\u015bliborski</option>
<option value="policki">policki</option>
<option value="pyrzycki">pyrzycki</option>
<option value="slawienski">s\u0142awie\u0144ski</option>
<option value="stargardzki">stargardzki</option>
<option value="szczecinecki">szczecinecki</option>
<option value="swidwinski">\u015bwidwi\u0144ski</option>
<option value="walecki">wa\u0142ecki</option>
</select>'''
        self.assertEqual(f.render('administrativeunit', 'katowice'), out)
    
    def test_PLPostalCodeField(self):
        error_format = [u'Enter a postal code in the format XX-XXX.']
        valid = {
            '41-403': '41-403',
        }
        invalid = {
            '43--434': error_format,
        }
        self.assertFieldOutput(PLPostalCodeField, valid, invalid)
    
    def test_PLNIPField(self):
        error_format = [u'Enter a tax number field (NIP) in the format XXX-XXX-XX-XX or XX-XX-XXX-XXX.']
        error_checksum = [u'Wrong checksum for the Tax Number (NIP).']
        valid = {
            '64-62-414-124': '6462414124',
            '646-241-41-24': '6462414124',
        }
        invalid = {
            '43-343-234-323': error_format,
            '646-241-41-23': error_checksum,
        }
        self.assertFieldOutput(PLNIPField, valid, invalid)
    
    def test_PLPESELField(self):
        error_checksum = [u'Wrong checksum for the National Identification Number.']
        error_format = [u'National Identification Number consists of 11 digits.']
        valid = {
            '80071610614': '80071610614',
        }
        invalid = {
            '80071610610': error_checksum,
            '80': error_format,
            '800716106AA': error_format,
        }
        self.assertFieldOutput(PLPESELField, valid, invalid)
    
    def test_PLREGONField(self):
        error_checksum = [u'Wrong checksum for the National Business Register Number (REGON).']
        error_format = [u'National Business Register Number (REGON) consists of 9 or 14 digits.']
        valid = {
            '12345678512347': '12345678512347',
            '590096454': '590096454',
        }
        invalid = {
            '123456784': error_checksum,
            '12345678412342': error_checksum,
            '590096453': error_checksum,
            '590096': error_format,
        }
        self.assertFieldOutput(PLREGONField, valid, invalid)

