import re


class PluralForms:
    """
    Represent Plural Forms, constructed from an already msgfmt-validated string.
    """
    PLACEHOLDER_STRING = '"Plural-Forms: nplurals=INTEGER; plural=EXPRESSION;\\n"'

    def __init__(self, raw_plural_form):
        self.full_string = raw_plural_form
        self.forms = {}
        self.nplurals = None
        if self.full_string != self.PLACEHOLDER_STRING:
            pf = re.sub(r'"\n"|"|\\n', "", raw_plural_form.strip(), re.MULTILINE)
            m = re.search(r'(?<=nplurals=)\d', pf)
            o = re.search(r'(?<=plural=)(.*?)(?=;|$)', pf)
            if m and o:
                self.nplurals = int(m.group(0))
                self.forms_string = o.group(0)
            else:
                # In some cases, msgfmt may consider valid forms without nplurals
                # or plurals (bug)
                raise ValueError(
                    "Unable to find 'nplurals' and/or 'plural' in the init string "
                    "(%s)." % raw_plural_form
                )
            forms = re.split(r'\s?:\s?', self.forms_string)
            forms = [self.trim_enclosing_parentheses(f) for f in forms]
            if len(forms) == 1 and self.nplurals == 1:
                self.forms[0] = forms[0]
            elif len(forms) == 1 and self.nplurals == 2:
                self.forms[0] = "SINGULAR"
                self.forms[1] = forms[0]
            else:
                for form in forms:
                    p = re.split(r'\s?\?\s?', form)
                    if len(p) == 1:
                        self.forms[int(p[0])] = "OTHER"
                    else:
                        self.forms[int(p[1])] = p[0]

    def __eq__(self, other):
        if other and self.nplurals == other.nplurals and self.forms == other.forms:
            return True
        else:
            return False

    def trim_enclosing_parentheses(self, form_string):
        """
        Trim all-forms enclosing parenthensis (if any).
        """
        counter = 0
        for char in form_string:
            if char == '(':
                counter += 1
            elif char == ')':
                counter -= 1
        if counter < 0:
            return form_string[:counter]
        elif counter > 0:
            return form_string[counter:]
        else:
            return form_string
