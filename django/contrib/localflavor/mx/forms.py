# -*- coding: utf-8 -*-
"""
Mexican-specific form helpers.
"""
import re

from django.forms import ValidationError
from django.forms.fields import Select, RegexField
from django.utils.translation import ugettext_lazy as _
from django.core.validators import EMPTY_VALUES
from django.contrib.localflavor.mx.mx_states import STATE_CHOICES

DATE_RE = r'\d{2}((01|03|05|07|08|10|12)(0[1-9]|[12]\d|3[01])|02(0[1-9]|[12]\d)|(04|06|09|11)(0[1-9]|[12]\d|30))'

"""
This is the list of inconvenient words according to the `Anexo IV` of the
document described in the next link:
    http://www.sisi.org.mx/jspsi/documentos/2005/seguimiento/06101/0610100162005_065.doc
"""

RFC_INCONVENIENT_WORDS = [
    u'BUEI', u'BUEY', u'CACA', u'CACO', u'CAGA', u'CAGO', u'CAKA', u'CAKO',
    u'COGE', u'COJA', u'COJE', u'COJI', u'COJO', u'CULO', u'FETO', u'GUEY',
    u'JOTO', u'KACA', u'KACO', u'KAGA', u'KAGO', u'KOGE', u'KOJO', u'KAKA',
    u'KULO', u'MAME', u'MAMO', u'MEAR', u'MEAS', u'MEON', u'MION', u'MOCO',
    u'MULA', u'PEDA', u'PEDO', u'PENE', u'PUTA', u'PUTO', u'QULO', u'RATA',
    u'RUIN',
]

"""
This is the list of inconvenient words according to the `Anexo 2` of the
document described in the next link:
    http://portal.veracruz.gob.mx/pls/portal/url/ITEM/444112558A57C6E0E040A8C02E00695C
"""
CURP_INCONVENIENT_WORDS = [
   u'BACA', u'BAKA', u'BUEI', u'BUEY', u'CACA', u'CACO', u'CAGA', u'CAGO',
   u'CAKA', u'CAKO', u'COGE', u'COGI', u'COJA', u'COJE', u'COJI', u'COJO',
   u'COLA', u'CULO', u'FALO', u'FETO', u'GETA', u'GUEI', u'GUEY', u'JETA',
   u'JOTO', u'KACA', u'KACO', u'KAGA', u'KAGO', u'KAKA', u'KAKO', u'KOGE',
   u'KOGI', u'KOJA', u'KOJE', u'KOJI', u'KOJO', u'KOLA', u'KULO', u'LILO',
   u'LOCA', u'LOCO', u'LOKA', u'LOKO', u'MAME', u'MAMO', u'MEAR', u'MEAS',
   u'MEON', u'MIAR', u'MION', u'MOCO', u'MOKO', u'MULA', u'MULO', u'NACA',
   u'NACO', u'PEDA', u'PEDO', u'PENE', u'PIPI', u'PITO', u'POPO', u'PUTA',
   u'PUTO', u'QULO', u'RATA', u'ROBA', u'ROBE', u'ROBO', u'RUIN', u'SENO',
   u'TETA', u'VACA', u'VAGA', u'VAGO', u'VAKA', u'VUEI', u'VUEY', u'WUEI',
   u'WUEY',
]

class MXStateSelect(Select):
    """
    A Select widget that uses a list of Mexican states as its choices.
    """
    def __init__(self, attrs=None):
        super(MXStateSelect, self).__init__(attrs, choices=STATE_CHOICES)


class MXZipCodeField(RegexField):
    """
    A form field that accepts a Mexican Zip Code.

    More info about this:
        http://en.wikipedia.org/wiki/List_of_postal_codes_in_Mexico
    """
    default_error_messages = {
        'invalid': _(u'Enter a valid zip code in the format XXXXX.'),
    }

    def __init__(self, *args, **kwargs):
        zip_code_re = ur'^(0[1-9]|[1][0-6]|[2-9]\d)(\d{3})$'
        super(MXZipCodeField, self).__init__(zip_code_re, *args, **kwargs)


class MXRFCField(RegexField):
    """
    A form field that validates a Mexican *Registro Federal de Contribuyentes*
    for either `Persona física` or `Persona moral`.

    The Persona física RFC string is integrated by a juxtaposition of
    characters following the next pattern:

        =====  ======  ===========================================
        Index  Format  Accepted Characters
        =====  ======  ===========================================
        1      X       Any letter
        2      X       Any vowel
        3-4    XX      Any letter
        5-10   YYMMDD  Any valid date
        11-12  XX      Any letter or number between 0 and 9
        13     X       Any digit between 0 and 9 or the letter *A*
        =====  ======  ===========================================

    The Persona moral RFC string is integrated by a juxtaposition of
    characters following the next pattern:

        =====  ======  ============================================
        Index  Format  Accepted Characters
        =====  ======  ============================================
        1-3    XXX     Any letter including *&* and *Ñ* chars
        4-9    YYMMDD  Any valid date
        10-11  XX      Any letter or number between 0 and 9
        12     X       Any number between 0 and 9 or the letter *A*
        =====  ======  ============================================

    More info about this:
        http://es.wikipedia.org/wiki/Registro_Federal_de_Contribuyentes_(M%C3%A9xico)
    """
    default_error_messages = {
        'invalid': _('Enter a valid RFC.'),
        'invalid_checksum': _('Invalid checksum for RFC.'),
    }

    def __init__(self, min_length=9, max_length=13, *args, **kwargs):
        rfc_re = re.compile(ur'^([A-Z&Ññ]{3}|[A-Z][AEIOU][A-Z]{2})%s([A-Z0-9]{2}[0-9A])?$' % DATE_RE,
                            re.IGNORECASE)
        super(MXRFCField, self).__init__(rfc_re, min_length=min_length,
                                         max_length=max_length, *args, **kwargs)

    def clean(self, value):
        value = super(MXRFCField, self).clean(value)
        if value in EMPTY_VALUES:
            return u''
        value = value.upper()
        if self._has_homoclave(value):
            if not value[-1] == self._checksum(value[:-1]):
                raise ValidationError(self.default_error_messages['invalid_checksum'])
        if self._has_inconvenient_word(value):
            raise ValidationError(self.default_error_messages['invalid'])
        return value

    def _has_homoclave(self, rfc):
        """
        This check is done due to the existance of RFCs without a *homoclave*
        since the current algorithm to calculate it had not been created for
        the first RFCs ever in Mexico.
        """
        rfc_without_homoclave_re = re.compile(ur'^[A-Z&Ññ]{3,4}%s$' % DATE_RE,
                                              re.IGNORECASE)
        return not rfc_without_homoclave_re.match(rfc)

    def _checksum(self, rfc):
        """
        More info about this procedure:
            www.sisi.org.mx/jspsi/documentos/2005/seguimiento/06101/0610100162005_065.doc
        """
        chars = u'0123456789ABCDEFGHIJKLMN&OPQRSTUVWXYZ-Ñ'
        if len(rfc) == 11:
            rfc = '-' + rfc

        sum_ = sum(i * chars.index(c) for i, c in zip(reversed(xrange(14)), rfc))
        checksum = 11 - sum_ % 11

        if checksum == 10:
            return u'A'
        elif checksum == 11:
            return u'0'

        return unicode(checksum)

    def _has_inconvenient_word(self, rfc):
        first_four = rfc[:4]
        return first_four in RFC_INCONVENIENT_WORDS


class MXCURPField(RegexField):
    """
    A field that validates a Mexican Clave Única de Registro de Población.

    The CURP is integrated by a juxtaposition of characters following the next
    pattern:

        =====  ======  ===================================================
        Index  Format  Accepted Characters
        =====  ======  ===================================================
        1      X       Any letter
        2      X       Any vowel
        3-4    XX      Any letter
        5-10   YYMMDD  Any valid date
        11     X       Either `H` or `M`, depending on the person's gender
        12-13  XX      Any valid acronym for a state in Mexico
        14-16  XXX     Any consonant
        17     X       Any number between 0 and 9 or any letter
        18     X       Any number between 0 and 9
        =====  ======  ===================================================

    More info about this:
        http://www.condusef.gob.mx/index.php/clave-unica-de-registro-de-poblacion-curp
    """
    default_error_messages = {
        'invalid': _('Enter a valid CURP.'),
        'invalid_checksum': _(u'Invalid checksum for CURP.'),
    }

    def __init__(self, min_length=18, max_length=18, *args, **kwargs):
        states_re = r'(AS|BC|BS|CC|CL|CM|CS|CH|DF|DG|GT|GR|HG|JC|MC|MN|MS|NT|NL|OC|PL|QT|QR|SP|SL|SR|TC|TS|TL|VZ|YN|ZS|NE)'
        consonants_re = r'[B-DF-HJ-NP-TV-Z]'
        curp_re = (ur'^[A-Z][AEIOU][A-Z]{2}%s[HM]%s%s{3}[0-9A-Z]\d$' %
                   (DATE_RE, states_re, consonants_re))
        curp_re = re.compile(curp_re, re.IGNORECASE)
        super(MXCURPField, self).__init__(curp_re, min_length=min_length,
                                          max_length=max_length, *args, **kwargs)

    def clean(self, value):
        value = super(MXCURPField, self).clean(value)
        if value in EMPTY_VALUES:
            return u''
        value = value.upper()
        if value[-1] != self._checksum(value[:-1]):
            raise ValidationError(self.default_error_messages['invalid_checksum'])
        if self._has_inconvenient_word(value):
            raise ValidationError(self.default_error_messages['invalid'])
        return value

    def _checksum(self, value):
        chars = u'0123456789ABCDEFGHIJKLMN&OPQRSTUVWXYZ'

        s = sum(i * chars.index(c) for i, c in zip(reversed(xrange(19)), value))
        checksum = 10 - s % 10

        if checksum == 10:
            return u'0'
        return unicode(checksum)

    def _has_inconvenient_word(self, curp):
        first_four = curp[:4]
        return first_four in CURP_INCONVENIENT_WORDS
