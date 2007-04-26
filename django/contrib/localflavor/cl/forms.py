"""
Chile specific form helpers.
"""
from django.newforms import ValidationError
from django.newforms.fields import RegexField, EMPTY_VALUES
from django.utils.translation import gettext

class CLRutField(RegexField):
    """
    Chilean "Rol Unico Tributario" (RUT) field. This is the Chilean national
    identification number.

    Samples for testing are available from
    https://palena.sii.cl/cvc/dte/ee_empresas_emisoras.html
    """
    def __init__(self, *args, **kwargs):
        if 'strict' in kwargs:
            del kwargs['strict']
            super(CLRutField, self).__init__(r'^(\d{1,2}\.)?\d{3}\.\d{3}-[\dkK]$',
                error_message=gettext('Enter valid a Chilean RUT. The format is XX.XXX.XXX-X.'),
                *args, **kwargs)
        else:
            # In non-strict mode, accept RUTs that validate but do not exist in
            # the real world.
            super(CLRutField, self).__init__(r'^[\d\.]{1,11}-?[\dkK]$', error_message=gettext(u'Enter valid a Chilean RUT'), *args, **kwargs)

    def clean(self, value):
        """
        Check and clean the chilean rut.
        """
        super(CLRutField, self).clean(value)
        if value in EMPTY_VALUES:
            return u''
        rut, verificador = self._canonify(value)
        if self._algorithm(rut) == verificador:
            return self._format(rut, verificador)
        else:
            raise ValidationError(u'The Chilean RUT is not valid.')

    def _algorithm(self, rut):
        """
        Takes RUT in pure canonical form, calculates the verifier digit.
        """
        suma  = 0
        multi = 2
        for r in rut[::-1]:
            suma  += int(r) * multi
            multi += 1
            if multi == 8:
                multi = 2
        return '0123456789K0'[11 - suma % 11]

    def _canonify(self, rut):
        """
        Turns the RUT into one normalized format. Returns a (rut, verifier)
        tuple.
        """
        rut = str(rut).replace(' ', '').replace('.', '').replace('-', '')
        return rut[:-1], rut[-1]

    def _format(self, code, verifier=None):
        """
        Formats the RUT from canonical form to the common string representation.
        If verifier=None, then the last digit in 'code' is the verifier.
        """
        if verifier is None:
            verifier = code[-1]
            code = code[:-1]
        while len(code) > 3 and '.' not in code[:3]:
            pos = code.find('.')
            if pos == -1:
                new_dot = -3
            else:
                new_dot = pos - 3
            code = code[:new_dot] + '.' + code[new_dot:]
        return '%s-%s' % (code, verifier)

