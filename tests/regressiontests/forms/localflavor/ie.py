# -*- coding: utf-8 -*-
# Tests for the contrib/localflavor/ie form fields.

tests = r"""
# IECountySelect #########################################################

>>> from django.contrib.localflavor.ie.forms import IECountySelect
>>> f = IECountySelect()
>>> f.render('counties', 'dublin')
u'<select name="counties">\n<option value="antrim">Antrim</option>\n<option value="armagh">Armagh</option>\n<option value="carlow">Carlow</option>\n<option value="cavan">Cavan</option>\n<option value="clare">Clare</option>\n<option value="cork">Cork</option>\n<option value="derry">Derry</option>\n<option value="donegal">Donegal</option>\n<option value="down">Down</option>\n<option value="dublin" selected="selected">Dublin</option>\n<option value="fermanagh">Fermanagh</option>\n<option value="galway">Galway</option>\n<option value="kerry">Kerry</option>\n<option value="kildare">Kildare</option>\n<option value="kilkenny">Kilkenny</option>\n<option value="laois">Laois</option>\n<option value="leitrim">Leitrim</option>\n<option value="limerick">Limerick</option>\n<option value="longford">Longford</option>\n<option value="louth">Louth</option>\n<option value="mayo">Mayo</option>\n<option value="meath">Meath</option>\n<option value="monaghan">Monaghan</option>\n<option value="offaly">Offaly</option>\n<option value="roscommon">Roscommon</option>\n<option value="sligo">Sligo</option>\n<option value="tipperary">Tipperary</option>\n<option value="tyrone">Tyrone</option>\n<option value="waterford">Waterford</option>\n<option value="westmeath">Westmeath</option>\n<option value="wexford">Wexford</option>\n<option value="wicklow">Wicklow</option>\n</select>'

"""
