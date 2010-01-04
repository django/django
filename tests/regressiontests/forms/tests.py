# -*- coding: utf-8 -*-
from extra import tests as extra_tests
from forms import tests as form_tests
from error_messages import tests as custom_error_message_tests
from localflavor.ar import tests as localflavor_ar_tests
from localflavor.at import tests as localflavor_at_tests
from localflavor.au import tests as localflavor_au_tests
from localflavor.br import tests as localflavor_br_tests
from localflavor.ca import tests as localflavor_ca_tests
from localflavor.ch import tests as localflavor_ch_tests
from localflavor.cl import tests as localflavor_cl_tests
from localflavor.cz import tests as localflavor_cz_tests
from localflavor.de import tests as localflavor_de_tests
from localflavor.es import tests as localflavor_es_tests
from localflavor.fi import tests as localflavor_fi_tests
from localflavor.fr import tests as localflavor_fr_tests
from localflavor.generic import tests as localflavor_generic_tests
from localflavor.id import tests as localflavor_id_tests
from localflavor.ie import tests as localflavor_ie_tests
from localflavor.is_ import tests as localflavor_is_tests
from localflavor.it import tests as localflavor_it_tests
from localflavor.jp import tests as localflavor_jp_tests
from localflavor.kw import tests as localflavor_kw_tests
from localflavor.nl import tests as localflavor_nl_tests
from localflavor.pl import tests as localflavor_pl_tests
from localflavor.pt import tests as localflavor_pt_tests
from localflavor.ro import tests as localflavor_ro_tests
from localflavor.se import tests as localflavor_se_tests
from localflavor.sk import tests as localflavor_sk_tests
from localflavor.uk import tests as localflavor_uk_tests
from localflavor.us import tests as localflavor_us_tests
from localflavor.uy import tests as localflavor_uy_tests
from localflavor.za import tests as localflavor_za_tests
from regressions import tests as regression_tests
from util import tests as util_tests
from widgets import tests as widgets_tests
from formsets import tests as formset_tests
from media import media_tests

from fields import FieldsTests
from validators import TestFieldWithValidators

__test__ = {
    'extra_tests': extra_tests,
    'form_tests': form_tests,
    'custom_error_message_tests': custom_error_message_tests,
    'localflavor_ar_tests': localflavor_ar_tests,
    'localflavor_at_tests': localflavor_at_tests,
    'localflavor_au_tests': localflavor_au_tests,
    'localflavor_br_tests': localflavor_br_tests,
    'localflavor_ca_tests': localflavor_ca_tests,
    'localflavor_ch_tests': localflavor_ch_tests,
    'localflavor_cl_tests': localflavor_cl_tests,
    'localflavor_cz_tests': localflavor_cz_tests,
    'localflavor_de_tests': localflavor_de_tests,
    'localflavor_es_tests': localflavor_es_tests,
    'localflavor_fi_tests': localflavor_fi_tests,
    'localflavor_fr_tests': localflavor_fr_tests,
    'localflavor_generic_tests': localflavor_generic_tests,
    'localflavor_id_tests': localflavor_id_tests,
    'localflavor_ie_tests': localflavor_ie_tests,
    'localflavor_is_tests': localflavor_is_tests,
    'localflavor_it_tests': localflavor_it_tests,
    'localflavor_jp_tests': localflavor_jp_tests,
    'localflavor_kw_tests': localflavor_kw_tests,
    'localflavor_nl_tests': localflavor_nl_tests,
    'localflavor_pl_tests': localflavor_pl_tests,
    'localflavor_pt_tests': localflavor_pt_tests,
    'localflavor_ro_tests': localflavor_ro_tests,
    'localflavor_se_tests': localflavor_se_tests,
    'localflavor_sk_tests': localflavor_sk_tests,
    'localflavor_uk_tests': localflavor_uk_tests,
    'localflavor_us_tests': localflavor_us_tests,
    'localflavor_uy_tests': localflavor_uy_tests,
    'localflavor_za_tests': localflavor_za_tests,
    'regression_tests': regression_tests,
    'formset_tests': formset_tests,
    'media_tests': media_tests,
    'util_tests': util_tests,
    'widgets_tests': widgets_tests,
}

if __name__ == "__main__":
    import doctest
    doctest.testmod()
