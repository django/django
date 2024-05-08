# $Id: ka.py 9444 2023-08-23 12:02:41Z grubert $
# Author: Temuri Doghonadze <temuri.doghonadze@gmail.com>
# Copyright: This module has been placed in the public domain.

# New language mappings are welcome.  Before doing a new translation, please
# read <https://docutils.sourceforge.io/docs/howto/i18n.html>.
# Two files must be translated for each language: one in docutils/languages,
# the other in docutils/parsers/rst/languages.

"""
Georgian-language mappings for language-dependent features of
reStructuredText.
"""

__docformat__ = 'reStructuredText'

directives = {
    'ხაზების-ბლოკი': 'line-block',
    'მეტა': 'meta',
    'მათემატიკა': 'math',
    'დამუშავებული-ლიტერალი': 'parsed-literal',
    'გამოყოფილი-ციტატა': 'pull-quote',
    'კოდი': 'code',
    'შერეული': 'compound',
    'კონტეინერი': 'container',
    'ცხრილი': 'table',
    'csv-ცხრილი': 'csv-table',
    'ჩამონათვალი-ცხრილი': 'list-table',
    'დაუმუშავებელი': 'raw',
    'ჩანაცვლება': 'replace',
    'restructuredtext-ის-სატესტო-დირექტივა': 'restructuredtext-test-directive',
    'სამიზნე-შენიშვნები': 'target-notes',
    'უნიკოდი': 'unicode',
    'თარიღი': 'date',
    'გვერდითი-პანელი': 'sidebar',
    'მნიშვნელოვანი': 'important',
    'ჩასმა': 'include',
    'ყურადღება': 'attention',
    'გამოკვეთა': 'highlights',
    'შენიშვნა': 'admonition',
    'გამოსახულება': 'image',
    'კლასი': 'class',
    'როლი': 'role',
    'ნაგულისხმევი-როლი': 'default-role',
    'სათაური': 'title',
    'განყ-ნომერი': 'sectnum',
    'განყ-ნომერი': 'sectnum',
    'საფრთხე': 'danger',
    'ფრთხილად': 'caution',
    'შეცდომა': 'error',
    'მინიშნება': 'tip',
    'ყურადღებით': 'warning',
    'აღნიშვნა': 'note',
    'ფიგურა': 'figure',
    'რუბრიკა': 'rubric',
    'რჩევა': 'hint',
    'შემცველობა': 'contents',
    'თემა': 'topic',
    'ეპიგრაფი': 'epigraph',
    'თავსართი': 'header',
    'ქვედა კოლონტიტული': 'footer',
    }
"""Georgian name to registered (in directives/__init__.py) directive name
mapping."""

roles = {
    'აკრონიმი': 'acronym',
    'კოდი': 'code',
    'ანონიმური-მიმართვა': 'anonymous-reference',
    'სიტყვასიტყვითი': 'literal',
    'მათემატიკა': 'math',
    'ზედა-ინდექსი': 'superscript',
    'მახვილი': 'emphasis',
    'სახელიანი-მიმართვა': 'named-reference',
    'ინდექსი': 'index',
    'ქვედა-ინდექსი': 'subscript',
    'სქელი-ფონტი': 'strong',
    'აბრევიატურა': 'abbreviation',
    'ჩანაცვლების-მიმართვა': 'substitution-reference',
    'pep-მიმართვა': 'pep-reference',
    'rfc-მიმართვა	': 'rfc-reference',
    'uri-მიმართვა': 'uri-reference',
    'title-მიმართვა': 'title-reference',
    'ქვედა-კოლონტიტულზე-მიმართვა': 'footnote-reference',
    'ციტატაზე-მიმართვა': 'citation-reference',
    'სამიზნე': 'target',
    'დაუმუშავებელი': 'raw',
    }
"""Mapping of Georgian role names to canonical role names for interpreted text.
"""
