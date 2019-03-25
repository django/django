# -*- coding: utf-8 -*-
"""
    sphinx.search.ja
    ~~~~~~~~~~~~~~~~

    Japanese search language: includes routine to split words.

    :copyright: Copyright 2007-2019 by the Sphinx team, see AUTHORS.
    :license: BSD, see LICENSE for details.
"""

# Python Version of TinySegmenter
# (http://chasen.org/~taku/software/TinySegmenter/)
# TinySegmenter is super compact Japanese tokenizer.
#
# TinySegmenter was originally developed by Taku Kudo <taku(at)chasen.org>.
# Python Version was developed by xnights <programming.magic(at)gmail.com>.
# For details, see http://programming-magic.com/?id=170

import os
import re
import sys
import warnings

from six import iteritems, PY3

try:
    import MeCab
    native_module = True
except ImportError:
    native_module = False

try:
    import janome.tokenizer
    janome_module = True
except ImportError:
    janome_module = False

from sphinx.deprecation import RemovedInSphinx30Warning
from sphinx.errors import SphinxError, ExtensionError
from sphinx.search import SearchLanguage
from sphinx.util import import_object

if False:
    # For type annotation
    from typing import Any, Dict, List  # NOQA


class BaseSplitter(object):

    def __init__(self, options):
        # type: (Dict) -> None
        self.options = options

    def split(self, input):
        # type: (unicode) -> List[unicode]
        """

        :param str input:
        :return:
        :rtype: list[str]
        """
        raise NotImplementedError


class MecabSplitter(BaseSplitter):
    def __init__(self, options):
        # type: (Dict) -> None
        super(MecabSplitter, self).__init__(options)
        self.ctypes_libmecab = None     # type: Any
        self.ctypes_mecab = None        # type: Any
        if not native_module:
            self.init_ctypes(options)
        else:
            self.init_native(options)
        self.dict_encode = options.get('dic_enc', 'utf-8')

    def split(self, input):
        # type: (unicode) -> List[unicode]
        input2 = input if PY3 else input.encode(self.dict_encode)
        if native_module:
            result = self.native.parse(input2)
        else:
            result = self.ctypes_libmecab.mecab_sparse_tostr(
                self.ctypes_mecab, input.encode(self.dict_encode))
        if PY3:
            return result.split(' ')
        else:
            return result.decode(self.dict_encode).split(' ')

    def init_native(self, options):
        # type: (Dict) -> None
        param = '-Owakati'
        dict = options.get('dict')
        if dict:
            param += ' -d %s' % dict
        self.native = MeCab.Tagger(param)

    def init_ctypes(self, options):
        # type: (Dict) -> None
        import ctypes.util

        lib = options.get('lib')

        if lib is None:
            if sys.platform.startswith('win'):
                libname = 'libmecab.dll'
            else:
                libname = 'mecab'
            libpath = ctypes.util.find_library(libname)
        elif os.path.basename(lib) == lib:
            libpath = ctypes.util.find_library(lib)
        else:
            libpath = None
            if os.path.exists(lib):
                libpath = lib
        if libpath is None:
            raise RuntimeError('MeCab dynamic library is not available')

        param = 'mecab -Owakati'
        dict = options.get('dict')
        if dict:
            param += ' -d %s' % dict

        fs_enc = sys.getfilesystemencoding() or sys.getdefaultencoding()

        self.ctypes_libmecab = ctypes.CDLL(libpath)
        self.ctypes_libmecab.mecab_new2.argtypes = (ctypes.c_char_p,)
        self.ctypes_libmecab.mecab_new2.restype = ctypes.c_void_p
        self.ctypes_libmecab.mecab_sparse_tostr.argtypes = (ctypes.c_void_p, ctypes.c_char_p)
        self.ctypes_libmecab.mecab_sparse_tostr.restype = ctypes.c_char_p
        self.ctypes_mecab = self.ctypes_libmecab.mecab_new2(param.encode(fs_enc))
        if self.ctypes_mecab is None:
            raise SphinxError('mecab initialization failed')

    def __del__(self):
        # type: () -> None
        if self.ctypes_libmecab:
            self.ctypes_libmecab.mecab_destroy(self.ctypes_mecab)

MeCabBinder = MecabSplitter  # keep backward compatibility until Sphinx-1.6


class JanomeSplitter(BaseSplitter):
    def __init__(self, options):
        # type: (Dict) -> None
        super(JanomeSplitter, self).__init__(options)
        self.user_dict = options.get('user_dic')
        self.user_dict_enc = options.get('user_dic_enc', 'utf8')
        self.init_tokenizer()

    def init_tokenizer(self):
        # type: () -> None
        if not janome_module:
            raise RuntimeError('Janome is not available')
        self.tokenizer = janome.tokenizer.Tokenizer(udic=self.user_dict, udic_enc=self.user_dict_enc)

    def split(self, input):
        # type: (unicode) -> List[unicode]
        result = u' '.join(token.surface for token in self.tokenizer.tokenize(input))
        return result.split(u' ')


class DefaultSplitter(BaseSplitter):
    patterns_ = dict([(re.compile(pattern), value) for pattern, value in iteritems({
        u'[一二三四五六七八九十百千万億兆]': u'M',
        u'[一-龠々〆ヵヶ]': u'H',
        u'[ぁ-ん]': u'I',
        u'[ァ-ヴーｱ-ﾝﾞｰ]': u'K',
        u'[a-zA-Zａ-ｚＡ-Ｚ]': u'A',
        u'[0-9０-９]': u'N',
    })])
    BIAS__ = -332
    BC1__ = {u'HH': 6, u'II': 2461, u'KH': 406, u'OH': -1378}
    BC2__ = {u'AA': -3267, u'AI': 2744, u'AN': -878, u'HH': -4070, u'HM': -1711,
             u'HN': 4012, u'HO': 3761, u'IA': 1327, u'IH': -1184, u'II': -1332,
             u'IK': 1721, u'IO': 5492, u'KI': 3831, u'KK': -8741, u'MH': -3132,
             u'MK': 3334, u'OO': -2920}
    BC3__ = {u'HH': 996, u'HI': 626, u'HK': -721, u'HN': -1307, u'HO': -836, u'IH': -301,
             u'KK': 2762, u'MK': 1079, u'MM': 4034, u'OA': -1652, u'OH': 266}
    BP1__ = {u'BB': 295, u'OB': 304, u'OO': -125, u'UB': 352}
    BP2__ = {u'BO': 60, u'OO': -1762}
    BQ1__ = {u'BHH': 1150, u'BHM': 1521, u'BII': -1158, u'BIM': 886, u'BMH': 1208,
             u'BNH': 449, u'BOH': -91, u'BOO': -2597, u'OHI': 451, u'OIH': -296,
             u'OKA': 1851, u'OKH': -1020, u'OKK': 904, u'OOO': 2965}
    BQ2__ = {u'BHH': 118, u'BHI': -1159, u'BHM': 466, u'BIH': -919, u'BKK': -1720,
             u'BKO': 864, u'OHH': -1139, u'OHM': -181, u'OIH': 153, u'UHI': -1146}
    BQ3__ = {u'BHH': -792, u'BHI': 2664, u'BII': -299, u'BKI': 419, u'BMH': 937,
             u'BMM': 8335, u'BNN': 998, u'BOH': 775, u'OHH': 2174, u'OHM': 439, u'OII': 280,
             u'OKH': 1798, u'OKI': -793, u'OKO': -2242, u'OMH': -2402, u'OOO': 11699}
    BQ4__ = {u'BHH': -3895, u'BIH': 3761, u'BII': -4654, u'BIK': 1348, u'BKK': -1806,
             u'BMI': -3385, u'BOO': -12396, u'OAH': 926, u'OHH': 266, u'OHK': -2036,
             u'ONN': -973}
    BW1__ = {u',と': 660, u',同': 727, u'B1あ': 1404, u'B1同': 542, u'、と': 660,
             u'、同': 727, u'」と': 1682, u'あっ': 1505, u'いう': 1743, u'いっ': -2055,
             u'いる': 672, u'うし': -4817, u'うん': 665, u'から': 3472, u'がら': 600,
             u'こう': -790, u'こと': 2083, u'こん': -1262, u'さら': -4143, u'さん': 4573,
             u'した': 2641, u'して': 1104, u'すで': -3399, u'そこ': 1977, u'それ': -871,
             u'たち': 1122, u'ため': 601, u'った': 3463, u'つい': -802, u'てい': 805,
             u'てき': 1249, u'でき': 1127, u'です': 3445, u'では': 844, u'とい': -4915,
             u'とみ': 1922, u'どこ': 3887, u'ない': 5713, u'なっ': 3015, u'など': 7379,
             u'なん': -1113, u'にし': 2468, u'には': 1498, u'にも': 1671, u'に対': -912,
             u'の一': -501, u'の中': 741, u'ませ': 2448, u'まで': 1711, u'まま': 2600,
             u'まる': -2155, u'やむ': -1947, u'よっ': -2565, u'れた': 2369, u'れで': -913,
             u'をし': 1860, u'を見': 731, u'亡く': -1886, u'京都': 2558, u'取り': -2784,
             u'大き': -2604, u'大阪': 1497, u'平方': -2314, u'引き': -1336, u'日本': -195,
             u'本当': -2423, u'毎日': -2113, u'目指': -724, u'Ｂ１あ': 1404, u'Ｂ１同': 542,
             u'｣と': 1682}
    BW2__ = {u'..': -11822, u'11': -669, u'――': -5730, u'−−': -13175, u'いう': -1609,
             u'うか': 2490, u'かし': -1350, u'かも': -602, u'から': -7194, u'かれ': 4612,
             u'がい': 853, u'がら': -3198, u'きた': 1941, u'くな': -1597, u'こと': -8392,
             u'この': -4193, u'させ': 4533, u'され': 13168, u'さん': -3977, u'しい': -1819,
             u'しか': -545, u'した': 5078, u'して': 972, u'しな': 939, u'その': -3744,
             u'たい': -1253, u'たた': -662, u'ただ': -3857, u'たち': -786, u'たと': 1224,
             u'たは': -939, u'った': 4589, u'って': 1647, u'っと': -2094, u'てい': 6144,
             u'てき': 3640, u'てく': 2551, u'ては': -3110, u'ても': -3065, u'でい': 2666,
             u'でき': -1528, u'でし': -3828, u'です': -4761, u'でも': -4203, u'とい': 1890,
             u'とこ': -1746, u'とと': -2279, u'との': 720, u'とみ': 5168, u'とも': -3941,
             u'ない': -2488, u'なが': -1313, u'など': -6509, u'なの': 2614, u'なん': 3099,
             u'にお': -1615, u'にし': 2748, u'にな': 2454, u'によ': -7236, u'に対': -14943,
             u'に従': -4688, u'に関': -11388, u'のか': 2093, u'ので': -7059, u'のに': -6041,
             u'のの': -6125, u'はい': 1073, u'はが': -1033, u'はず': -2532, u'ばれ': 1813,
             u'まし': -1316, u'まで': -6621, u'まれ': 5409, u'めて': -3153, u'もい': 2230,
             u'もの': -10713, u'らか': -944, u'らし': -1611, u'らに': -1897, u'りし': 651,
             u'りま': 1620, u'れた': 4270, u'れて': 849, u'れば': 4114, u'ろう': 6067,
             u'われ': 7901, u'を通': -11877, u'んだ': 728, u'んな': -4115, u'一人': 602,
             u'一方': -1375, u'一日': 970, u'一部': -1051, u'上が': -4479, u'会社': -1116,
             u'出て': 2163, u'分の': -7758, u'同党': 970, u'同日': -913, u'大阪': -2471,
             u'委員': -1250, u'少な': -1050, u'年度': -8669, u'年間': -1626, u'府県': -2363,
             u'手権': -1982, u'新聞': -4066, u'日新': -722, u'日本': -7068, u'日米': 3372,
             u'曜日': -601, u'朝鮮': -2355, u'本人': -2697, u'東京': -1543, u'然と': -1384,
             u'社会': -1276, u'立て': -990, u'第に': -1612, u'米国': -4268, u'１１': -669}
    BW3__ = {u'あた': -2194, u'あり': 719, u'ある': 3846, u'い.': -1185, u'い。': -1185,
             u'いい': 5308, u'いえ': 2079, u'いく': 3029, u'いた': 2056, u'いっ': 1883,
             u'いる': 5600, u'いわ': 1527, u'うち': 1117, u'うと': 4798, u'えと': 1454,
             u'か.': 2857, u'か。': 2857, u'かけ': -743, u'かっ': -4098, u'かに': -669,
             u'から': 6520, u'かり': -2670, u'が,': 1816, u'が、': 1816, u'がき': -4855,
             u'がけ': -1127, u'がっ': -913, u'がら': -4977, u'がり': -2064, u'きた': 1645,
             u'けど': 1374, u'こと': 7397, u'この': 1542, u'ころ': -2757, u'さい': -714,
             u'さを': 976, u'し,': 1557, u'し、': 1557, u'しい': -3714, u'した': 3562,
             u'して': 1449, u'しな': 2608, u'しま': 1200, u'す.': -1310, u'す。': -1310,
             u'する': 6521, u'ず,': 3426, u'ず、': 3426, u'ずに': 841, u'そう': 428,
             u'た.': 8875, u'た。': 8875, u'たい': -594, u'たの': 812, u'たり': -1183,
             u'たる': -853, u'だ.': 4098, u'だ。': 4098, u'だっ': 1004, u'った': -4748,
             u'って': 300, u'てい': 6240, u'てお': 855, u'ても': 302, u'です': 1437,
             u'でに': -1482, u'では': 2295, u'とう': -1387, u'とし': 2266, u'との': 541,
             u'とも': -3543, u'どう': 4664, u'ない': 1796, u'なく': -903, u'など': 2135,
             u'に,': -1021, u'に、': -1021, u'にし': 1771, u'にな': 1906, u'には': 2644,
             u'の,': -724, u'の、': -724, u'の子': -1000, u'は,': 1337, u'は、': 1337,
             u'べき': 2181, u'まし': 1113, u'ます': 6943, u'まっ': -1549, u'まで': 6154,
             u'まれ': -793, u'らし': 1479, u'られ': 6820, u'るる': 3818, u'れ,': 854,
             u'れ、': 854, u'れた': 1850, u'れて': 1375, u'れば': -3246, u'れる': 1091,
             u'われ': -605, u'んだ': 606, u'んで': 798, u'カ月': 990, u'会議': 860,
             u'入り': 1232, u'大会': 2217, u'始め': 1681, u'市': 965, u'新聞': -5055,
             u'日,': 974, u'日、': 974, u'社会': 2024, u'ｶ月': 990}
    TC1__ = {u'AAA': 1093, u'HHH': 1029, u'HHM': 580, u'HII': 998, u'HOH': -390,
             u'HOM': -331, u'IHI': 1169, u'IOH': -142, u'IOI': -1015, u'IOM': 467,
             u'MMH': 187, u'OOI': -1832}
    TC2__ = {u'HHO': 2088, u'HII': -1023, u'HMM': -1154, u'IHI': -1965,
             u'KKH': 703, u'OII': -2649}
    TC3__ = {u'AAA': -294, u'HHH': 346, u'HHI': -341, u'HII': -1088, u'HIK': 731,
             u'HOH': -1486, u'IHH': 128, u'IHI': -3041, u'IHO': -1935, u'IIH': -825,
             u'IIM': -1035, u'IOI': -542, u'KHH': -1216, u'KKA': 491, u'KKH': -1217,
             u'KOK': -1009, u'MHH': -2694, u'MHM': -457, u'MHO': 123, u'MMH': -471,
             u'NNH': -1689, u'NNO': 662, u'OHO': -3393}
    TC4__ = {u'HHH': -203, u'HHI': 1344, u'HHK': 365, u'HHM': -122, u'HHN': 182,
             u'HHO': 669, u'HIH': 804, u'HII': 679, u'HOH': 446, u'IHH': 695,
             u'IHO': -2324, u'IIH': 321, u'III': 1497, u'IIO': 656, u'IOO': 54,
             u'KAK': 4845, u'KKA': 3386, u'KKK': 3065, u'MHH': -405, u'MHI': 201,
             u'MMH': -241, u'MMM': 661, u'MOM': 841}
    TQ1__ = {u'BHHH': -227, u'BHHI': 316, u'BHIH': -132, u'BIHH': 60, u'BIII': 1595,
             u'BNHH': -744, u'BOHH': 225, u'BOOO': -908, u'OAKK': 482, u'OHHH': 281,
             u'OHIH': 249, u'OIHI': 200, u'OIIH': -68}
    TQ2__ = {u'BIHH': -1401, u'BIII': -1033, u'BKAK': -543, u'BOOO': -5591}
    TQ3__ = {u'BHHH': 478, u'BHHM': -1073, u'BHIH': 222, u'BHII': -504, u'BIIH': -116,
             u'BIII': -105, u'BMHI': -863, u'BMHM': -464, u'BOMH': 620, u'OHHH': 346,
             u'OHHI': 1729, u'OHII': 997, u'OHMH': 481, u'OIHH': 623, u'OIIH': 1344,
             u'OKAK': 2792, u'OKHH': 587, u'OKKA': 679, u'OOHH': 110, u'OOII': -685}
    TQ4__ = {u'BHHH': -721, u'BHHM': -3604, u'BHII': -966, u'BIIH': -607, u'BIII': -2181,
             u'OAAA': -2763, u'OAKK': 180, u'OHHH': -294, u'OHHI': 2446, u'OHHO': 480,
             u'OHIH': -1573, u'OIHH': 1935, u'OIHI': -493, u'OIIH': 626, u'OIII': -4007,
             u'OKAK': -8156}
    TW1__ = {u'につい': -4681, u'東京都': 2026}
    TW2__ = {u'ある程': -2049, u'いった': -1256, u'ころが': -2434, u'しょう': 3873,
             u'その後': -4430, u'だって': -1049, u'ていた': 1833, u'として': -4657,
             u'ともに': -4517, u'もので': 1882, u'一気に': -792, u'初めて': -1512,
             u'同時に': -8097, u'大きな': -1255, u'対して': -2721, u'社会党': -3216}
    TW3__ = {u'いただ': -1734, u'してい': 1314, u'として': -4314, u'につい': -5483,
             u'にとっ': -5989, u'に当た': -6247, u'ので,': -727, u'ので、': -727,
             u'のもの': -600, u'れから': -3752, u'十二月': -2287}
    TW4__ = {u'いう.': 8576, u'いう。': 8576, u'からな': -2348, u'してい': 2958,
             u'たが,': 1516, u'たが、': 1516, u'ている': 1538, u'という': 1349,
             u'ました': 5543, u'ません': 1097, u'ようと': -4258, u'よると': 5865}
    UC1__ = {u'A': 484, u'K': 93, u'M': 645, u'O': -505}
    UC2__ = {u'A': 819, u'H': 1059, u'I': 409, u'M': 3987, u'N': 5775, u'O': 646}
    UC3__ = {u'A': -1370, u'I': 2311}
    UC4__ = {u'A': -2643, u'H': 1809, u'I': -1032, u'K': -3450, u'M': 3565,
             u'N': 3876, u'O': 6646}
    UC5__ = {u'H': 313, u'I': -1238, u'K': -799, u'M': 539, u'O': -831}
    UC6__ = {u'H': -506, u'I': -253, u'K': 87, u'M': 247, u'O': -387}
    UP1__ = {u'O': -214}
    UP2__ = {u'B': 69, u'O': 935}
    UP3__ = {u'B': 189}
    UQ1__ = {u'BH': 21, u'BI': -12, u'BK': -99, u'BN': 142, u'BO': -56, u'OH': -95,
             u'OI': 477, u'OK': 410, u'OO': -2422}
    UQ2__ = {u'BH': 216, u'BI': 113, u'OK': 1759}
    UQ3__ = {u'BA': -479, u'BH': 42, u'BI': 1913, u'BK': -7198, u'BM': 3160,
             u'BN': 6427, u'BO': 14761, u'OI': -827, u'ON': -3212}
    UW1__ = {u',': 156, u'、': 156, u'「': -463, u'あ': -941, u'う': -127, u'が': -553,
             u'き': 121, u'こ': 505, u'で': -201, u'と': -547, u'ど': -123, u'に': -789,
             u'の': -185, u'は': -847, u'も': -466, u'や': -470, u'よ': 182, u'ら': -292,
             u'り': 208, u'れ': 169, u'を': -446, u'ん': -137, u'・': -135, u'主': -402,
             u'京': -268, u'区': -912, u'午': 871, u'国': -460, u'大': 561, u'委': 729,
             u'市': -411, u'日': -141, u'理': 361, u'生': -408, u'県': -386, u'都': -718,
             u'｢': -463, u'･': -135}
    UW2__ = {u',': -829, u'、': -829, u'〇': 892, u'「': -645, u'」': 3145, u'あ': -538,
             u'い': 505, u'う': 134, u'お': -502, u'か': 1454, u'が': -856, u'く': -412,
             u'こ': 1141, u'さ': 878, u'ざ': 540, u'し': 1529, u'す': -675, u'せ': 300,
             u'そ': -1011, u'た': 188, u'だ': 1837, u'つ': -949, u'て': -291, u'で': -268,
             u'と': -981, u'ど': 1273, u'な': 1063, u'に': -1764, u'の': 130, u'は': -409,
             u'ひ': -1273, u'べ': 1261, u'ま': 600, u'も': -1263, u'や': -402, u'よ': 1639,
             u'り': -579, u'る': -694, u'れ': 571, u'を': -2516, u'ん': 2095, u'ア': -587,
             u'カ': 306, u'キ': 568, u'ッ': 831, u'三': -758, u'不': -2150, u'世': -302,
             u'中': -968, u'主': -861, u'事': 492, u'人': -123, u'会': 978, u'保': 362,
             u'入': 548, u'初': -3025, u'副': -1566, u'北': -3414, u'区': -422, u'大': -1769,
             u'天': -865, u'太': -483, u'子': -1519, u'学': 760, u'実': 1023, u'小': -2009,
             u'市': -813, u'年': -1060, u'強': 1067, u'手': -1519, u'揺': -1033, u'政': 1522,
             u'文': -1355, u'新': -1682, u'日': -1815, u'明': -1462, u'最': -630, u'朝': -1843,
             u'本': -1650, u'東': -931, u'果': -665, u'次': -2378, u'民': -180, u'気': -1740,
             u'理': 752, u'発': 529, u'目': -1584, u'相': -242, u'県': -1165, u'立': -763,
             u'第': 810, u'米': 509, u'自': -1353, u'行': 838, u'西': -744, u'見': -3874,
             u'調': 1010, u'議': 1198, u'込': 3041, u'開': 1758, u'間': -1257, u'｢': -645,
             u'｣': 3145, u'ｯ': 831, u'ｱ': -587, u'ｶ': 306, u'ｷ': 568}
    UW3__ = {u',': 4889, u'1': -800, u'−': -1723, u'、': 4889, u'々': -2311, u'〇': 5827,
             u'」': 2670, u'〓': -3573, u'あ': -2696, u'い': 1006, u'う': 2342, u'え': 1983,
             u'お': -4864, u'か': -1163, u'が': 3271, u'く': 1004, u'け': 388, u'げ': 401,
             u'こ': -3552, u'ご': -3116, u'さ': -1058, u'し': -395, u'す': 584, u'せ': 3685,
             u'そ': -5228, u'た': 842, u'ち': -521, u'っ': -1444, u'つ': -1081, u'て': 6167,
             u'で': 2318, u'と': 1691, u'ど': -899, u'な': -2788, u'に': 2745, u'の': 4056,
             u'は': 4555, u'ひ': -2171, u'ふ': -1798, u'へ': 1199, u'ほ': -5516, u'ま': -4384,
             u'み': -120, u'め': 1205, u'も': 2323, u'や': -788, u'よ': -202, u'ら': 727,
             u'り': 649, u'る': 5905, u'れ': 2773, u'わ': -1207, u'を': 6620, u'ん': -518,
             u'ア': 551, u'グ': 1319, u'ス': 874, u'ッ': -1350, u'ト': 521, u'ム': 1109,
             u'ル': 1591, u'ロ': 2201, u'ン': 278, u'・': -3794, u'一': -1619, u'下': -1759,
             u'世': -2087, u'両': 3815, u'中': 653, u'主': -758, u'予': -1193, u'二': 974,
             u'人': 2742, u'今': 792, u'他': 1889, u'以': -1368, u'低': 811, u'何': 4265,
             u'作': -361, u'保': -2439, u'元': 4858, u'党': 3593, u'全': 1574, u'公': -3030,
             u'六': 755, u'共': -1880, u'円': 5807, u'再': 3095, u'分': 457, u'初': 2475,
             u'別': 1129, u'前': 2286, u'副': 4437, u'力': 365, u'動': -949, u'務': -1872,
             u'化': 1327, u'北': -1038, u'区': 4646, u'千': -2309, u'午': -783, u'協': -1006,
             u'口': 483, u'右': 1233, u'各': 3588, u'合': -241, u'同': 3906, u'和': -837,
             u'員': 4513, u'国': 642, u'型': 1389, u'場': 1219, u'外': -241, u'妻': 2016,
             u'学': -1356, u'安': -423, u'実': -1008, u'家': 1078, u'小': -513, u'少': -3102,
             u'州': 1155, u'市': 3197, u'平': -1804, u'年': 2416, u'広': -1030, u'府': 1605,
             u'度': 1452, u'建': -2352, u'当': -3885, u'得': 1905, u'思': -1291, u'性': 1822,
             u'戸': -488, u'指': -3973, u'政': -2013, u'教': -1479, u'数': 3222, u'文': -1489,
             u'新': 1764, u'日': 2099, u'旧': 5792, u'昨': -661, u'時': -1248, u'曜': -951,
             u'最': -937, u'月': 4125, u'期': 360, u'李': 3094, u'村': 364, u'東': -805,
             u'核': 5156, u'森': 2438, u'業': 484, u'氏': 2613, u'民': -1694, u'決': -1073,
             u'法': 1868, u'海': -495, u'無': 979, u'物': 461, u'特': -3850, u'生': -273,
             u'用': 914, u'町': 1215, u'的': 7313, u'直': -1835, u'省': 792, u'県': 6293,
             u'知': -1528, u'私': 4231, u'税': 401, u'立': -960, u'第': 1201, u'米': 7767,
             u'系': 3066, u'約': 3663, u'級': 1384, u'統': -4229, u'総': 1163, u'線': 1255,
             u'者': 6457, u'能': 725, u'自': -2869, u'英': 785, u'見': 1044, u'調': -562,
             u'財': -733, u'費': 1777, u'車': 1835, u'軍': 1375, u'込': -1504, u'通': -1136,
             u'選': -681, u'郎': 1026, u'郡': 4404, u'部': 1200, u'金': 2163, u'長': 421,
             u'開': -1432, u'間': 1302, u'関': -1282, u'雨': 2009, u'電': -1045, u'非': 2066,
             u'駅': 1620, u'１': -800, u'｣': 2670, u'･': -3794, u'ｯ': -1350, u'ｱ': 551,
             u'ｸﾞ': 1319, u'ｽ': 874, u'ﾄ': 521, u'ﾑ': 1109, u'ﾙ': 1591, u'ﾛ': 2201, u'ﾝ': 278}
    UW4__ = {u',': 3930, u'.': 3508, u'―': -4841, u'、': 3930, u'。': 3508, u'〇': 4999,
             u'「': 1895, u'」': 3798, u'〓': -5156, u'あ': 4752, u'い': -3435, u'う': -640,
             u'え': -2514, u'お': 2405, u'か': 530, u'が': 6006, u'き': -4482, u'ぎ': -3821,
             u'く': -3788, u'け': -4376, u'げ': -4734, u'こ': 2255, u'ご': 1979, u'さ': 2864,
             u'し': -843, u'じ': -2506, u'す': -731, u'ず': 1251, u'せ': 181, u'そ': 4091,
             u'た': 5034, u'だ': 5408, u'ち': -3654, u'っ': -5882, u'つ': -1659, u'て': 3994,
             u'で': 7410, u'と': 4547, u'な': 5433, u'に': 6499, u'ぬ': 1853, u'ね': 1413,
             u'の': 7396, u'は': 8578, u'ば': 1940, u'ひ': 4249, u'び': -4134, u'ふ': 1345,
             u'へ': 6665, u'べ': -744, u'ほ': 1464, u'ま': 1051, u'み': -2082, u'む': -882,
             u'め': -5046, u'も': 4169, u'ゃ': -2666, u'や': 2795, u'ょ': -1544, u'よ': 3351,
             u'ら': -2922, u'り': -9726, u'る': -14896, u'れ': -2613, u'ろ': -4570,
             u'わ': -1783, u'を': 13150, u'ん': -2352, u'カ': 2145, u'コ': 1789, u'セ': 1287,
             u'ッ': -724, u'ト': -403, u'メ': -1635, u'ラ': -881, u'リ': -541, u'ル': -856,
             u'ン': -3637, u'・': -4371, u'ー': -11870, u'一': -2069, u'中': 2210, u'予': 782,
             u'事': -190, u'井': -1768, u'人': 1036, u'以': 544, u'会': 950, u'体': -1286,
             u'作': 530, u'側': 4292, u'先': 601, u'党': -2006, u'共': -1212, u'内': 584,
             u'円': 788, u'初': 1347, u'前': 1623, u'副': 3879, u'力': -302, u'動': -740,
             u'務': -2715, u'化': 776, u'区': 4517, u'協': 1013, u'参': 1555, u'合': -1834,
             u'和': -681, u'員': -910, u'器': -851, u'回': 1500, u'国': -619, u'園': -1200,
             u'地': 866, u'場': -1410, u'塁': -2094, u'士': -1413, u'多': 1067, u'大': 571,
             u'子': -4802, u'学': -1397, u'定': -1057, u'寺': -809, u'小': 1910, u'屋': -1328,
             u'山': -1500, u'島': -2056, u'川': -2667, u'市': 2771, u'年': 374, u'庁': -4556,
             u'後': 456, u'性': 553, u'感': 916, u'所': -1566, u'支': 856, u'改': 787,
             u'政': 2182, u'教': 704, u'文': 522, u'方': -856, u'日': 1798, u'時': 1829,
             u'最': 845, u'月': -9066, u'木': -485, u'来': -442, u'校': -360, u'業': -1043,
             u'氏': 5388, u'民': -2716, u'気': -910, u'沢': -939, u'済': -543, u'物': -735,
             u'率': 672, u'球': -1267, u'生': -1286, u'産': -1101, u'田': -2900, u'町': 1826,
             u'的': 2586, u'目': 922, u'省': -3485, u'県': 2997, u'空': -867, u'立': -2112,
             u'第': 788, u'米': 2937, u'系': 786, u'約': 2171, u'経': 1146, u'統': -1169,
             u'総': 940, u'線': -994, u'署': 749, u'者': 2145, u'能': -730, u'般': -852,
             u'行': -792, u'規': 792, u'警': -1184, u'議': -244, u'谷': -1000, u'賞': 730,
             u'車': -1481, u'軍': 1158, u'輪': -1433, u'込': -3370, u'近': 929, u'道': -1291,
             u'選': 2596, u'郎': -4866, u'都': 1192, u'野': -1100, u'銀': -2213, u'長': 357,
             u'間': -2344, u'院': -2297, u'際': -2604, u'電': -878, u'領': -1659, u'題': -792,
             u'館': -1984, u'首': 1749, u'高': 2120, u'｢': 1895, u'｣': 3798, u'･': -4371,
             u'ｯ': -724, u'ｰ': -11870, u'ｶ': 2145, u'ｺ': 1789, u'ｾ': 1287, u'ﾄ': -403,
             u'ﾒ': -1635, u'ﾗ': -881, u'ﾘ': -541, u'ﾙ': -856, u'ﾝ': -3637}
    UW5__ = {u',': 465, u'.': -299, u'1': -514, u'E2': -32768, u']': -2762, u'、': 465,
             u'。': -299, u'「': 363, u'あ': 1655, u'い': 331, u'う': -503, u'え': 1199,
             u'お': 527, u'か': 647, u'が': -421, u'き': 1624, u'ぎ': 1971, u'く': 312,
             u'げ': -983, u'さ': -1537, u'し': -1371, u'す': -852, u'だ': -1186, u'ち': 1093,
             u'っ': 52, u'つ': 921, u'て': -18, u'で': -850, u'と': -127, u'ど': 1682,
             u'な': -787, u'に': -1224, u'の': -635, u'は': -578, u'べ': 1001, u'み': 502,
             u'め': 865, u'ゃ': 3350, u'ょ': 854, u'り': -208, u'る': 429, u'れ': 504,
             u'わ': 419, u'を': -1264, u'ん': 327, u'イ': 241, u'ル': 451, u'ン': -343,
             u'中': -871, u'京': 722, u'会': -1153, u'党': -654, u'務': 3519, u'区': -901,
             u'告': 848, u'員': 2104, u'大': -1296, u'学': -548, u'定': 1785, u'嵐': -1304,
             u'市': -2991, u'席': 921, u'年': 1763, u'思': 872, u'所': -814, u'挙': 1618,
             u'新': -1682, u'日': 218, u'月': -4353, u'査': 932, u'格': 1356, u'機': -1508,
             u'氏': -1347, u'田': 240, u'町': -3912, u'的': -3149, u'相': 1319, u'省': -1052,
             u'県': -4003, u'研': -997, u'社': -278, u'空': -813, u'統': 1955, u'者': -2233,
             u'表': 663, u'語': -1073, u'議': 1219, u'選': -1018, u'郎': -368, u'長': 786,
             u'間': 1191, u'題': 2368, u'館': -689, u'１': -514, u'Ｅ２': -32768, u'｢': 363,
             u'ｲ': 241, u'ﾙ': 451, u'ﾝ': -343}
    UW6__ = {u',': 227, u'.': 808, u'1': -270, u'E1': 306, u'、': 227, u'。': 808,
             u'あ': -307, u'う': 189, u'か': 241, u'が': -73, u'く': -121, u'こ': -200,
             u'じ': 1782, u'す': 383, u'た': -428, u'っ': 573, u'て': -1014, u'で': 101,
             u'と': -105, u'な': -253, u'に': -149, u'の': -417, u'は': -236, u'も': -206,
             u'り': 187, u'る': -135, u'を': 195, u'ル': -673, u'ン': -496, u'一': -277,
             u'中': 201, u'件': -800, u'会': 624, u'前': 302, u'区': 1792, u'員': -1212,
             u'委': 798, u'学': -960, u'市': 887, u'広': -695, u'後': 535, u'業': -697,
             u'相': 753, u'社': -507, u'福': 974, u'空': -822, u'者': 1811, u'連': 463,
             u'郎': 1082, u'１': -270, u'Ｅ１': 306, u'ﾙ': -673, u'ﾝ': -496}

    # ctype_
    def ctype_(self, char):
        # type: (unicode) -> unicode
        for pattern, value in iteritems(self.patterns_):
            if pattern.match(char):
                return value
        return u'O'

    # ts_
    def ts_(self, dict, key):
        # type: (Dict[unicode, int], unicode) -> int
        if key in dict:
            return dict[key]
        return 0

    # segment
    def split(self, input):
        # type: (unicode) -> List[unicode]
        if not input:
            return []

        result = []
        seg = [u'B3', u'B2', u'B1']
        ctype = [u'O', u'O', u'O']
        for t in input:
            seg.append(t)
            ctype.append(self.ctype_(t))
        seg.append(u'E1')
        seg.append(u'E2')
        seg.append(u'E3')
        ctype.append(u'O')
        ctype.append(u'O')
        ctype.append(u'O')
        word = seg[3]
        p1 = u'U'
        p2 = u'U'
        p3 = u'U'

        for i in range(4, len(seg) - 3):
            score = self.BIAS__
            w1 = seg[i-3]
            w2 = seg[i-2]
            w3 = seg[i-1]
            w4 = seg[i]
            w5 = seg[i+1]
            w6 = seg[i+2]
            c1 = ctype[i-3]
            c2 = ctype[i-2]
            c3 = ctype[i-1]
            c4 = ctype[i]
            c5 = ctype[i+1]
            c6 = ctype[i+2]
            score += self.ts_(self.UP1__, p1)
            score += self.ts_(self.UP2__, p2)
            score += self.ts_(self.UP3__, p3)
            score += self.ts_(self.BP1__, p1 + p2)
            score += self.ts_(self.BP2__, p2 + p3)
            score += self.ts_(self.UW1__, w1)
            score += self.ts_(self.UW2__, w2)
            score += self.ts_(self.UW3__, w3)
            score += self.ts_(self.UW4__, w4)
            score += self.ts_(self.UW5__, w5)
            score += self.ts_(self.UW6__, w6)
            score += self.ts_(self.BW1__, w2 + w3)
            score += self.ts_(self.BW2__, w3 + w4)
            score += self.ts_(self.BW3__, w4 + w5)
            score += self.ts_(self.TW1__, w1 + w2 + w3)
            score += self.ts_(self.TW2__, w2 + w3 + w4)
            score += self.ts_(self.TW3__, w3 + w4 + w5)
            score += self.ts_(self.TW4__, w4 + w5 + w6)
            score += self.ts_(self.UC1__, c1)
            score += self.ts_(self.UC2__, c2)
            score += self.ts_(self.UC3__, c3)
            score += self.ts_(self.UC4__, c4)
            score += self.ts_(self.UC5__, c5)
            score += self.ts_(self.UC6__, c6)
            score += self.ts_(self.BC1__, c2 + c3)
            score += self.ts_(self.BC2__, c3 + c4)
            score += self.ts_(self.BC3__, c4 + c5)
            score += self.ts_(self.TC1__, c1 + c2 + c3)
            score += self.ts_(self.TC2__, c2 + c3 + c4)
            score += self.ts_(self.TC3__, c3 + c4 + c5)
            score += self.ts_(self.TC4__, c4 + c5 + c6)
#           score += self.ts_(self.TC5__, c4 + c5 + c6)
            score += self.ts_(self.UQ1__, p1 + c1)
            score += self.ts_(self.UQ2__, p2 + c2)
            score += self.ts_(self.UQ1__, p3 + c3)
            score += self.ts_(self.BQ1__, p2 + c2 + c3)
            score += self.ts_(self.BQ2__, p2 + c3 + c4)
            score += self.ts_(self.BQ3__, p3 + c2 + c3)
            score += self.ts_(self.BQ4__, p3 + c3 + c4)
            score += self.ts_(self.TQ1__, p2 + c1 + c2 + c3)
            score += self.ts_(self.TQ2__, p2 + c2 + c3 + c4)
            score += self.ts_(self.TQ3__, p3 + c1 + c2 + c3)
            score += self.ts_(self.TQ4__, p3 + c2 + c3 + c4)
            p = u'O'
            if score > 0:
                result.append(word.strip())
                word = u''
                p = u'B'
            p1 = p2
            p2 = p3
            p3 = p
            word += seg[i]

        result.append(word.strip())
        return result


TinySegmenter = DefaultSplitter  # keep backward compatibility until Sphinx-1.6


class SearchJapanese(SearchLanguage):
    """
    Japanese search implementation: uses no stemmer, but word splitting is quite
    complicated.
    """
    lang = 'ja'
    language_name = 'Japanese'
    splitters = {
        'default': 'sphinx.search.ja.DefaultSplitter',
        'mecab': 'sphinx.search.ja.MecabSplitter',
        'janome': 'sphinx.search.ja.JanomeSplitter',
    }

    def init(self, options):
        # type: (Dict) -> None
        type = options.get('type', 'sphinx.search.ja.DefaultSplitter')
        if type in self.splitters:
            dotted_path = self.splitters[type]
            warnings.warn('html_search_options["type"]: %s is deprecated. '
                          'Please give "%s" instead.' % (type, dotted_path),
                          RemovedInSphinx30Warning, stacklevel=2)
        else:
            dotted_path = type
        try:
            self.splitter = import_object(dotted_path)(options)
        except ExtensionError:
            raise ExtensionError("Splitter module %r can't be imported" %
                                 dotted_path)

    def split(self, input):
        # type: (unicode) -> List[unicode]
        return self.splitter.split(input)

    def word_filter(self, stemmed_word):
        # type: (unicode) -> bool
        return len(stemmed_word) > 1

    def stem(self, word):
        # type: (unicode) -> unicode
        return word
