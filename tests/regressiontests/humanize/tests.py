import unittest
from django.template import Template, Context, add_to_builtins

add_to_builtins('django.contrib.humanize.templatetags.humanize')

class HumanizeTests(unittest.TestCase):

    def humanize_tester(self, test_list, result_list, method):
        # Using max below ensures we go through both lists
        # However, if the lists are not equal length, this raises an exception
        for index in xrange(len(max(test_list,result_list))):
            test_content = test_list[index]
            t = Template('{{ test_content|%s }}' % method)
            rendered = t.render(Context(locals())).strip()
            self.assertEqual(rendered, result_list[index],
                             msg="""%s test failed, produced %s,
should've produced %s""" % (method, rendered, result_list[index]))
    
    def test_ordinal(self):
        test_list = ('1','2','3','4','11','12',
                     '13','101','102','103','111',
                     'something else')
        result_list = ('1st', '2nd', '3rd', '4th', '11th',
                       '12th', '13th', '101st', '102nd', '103rd',
                       '111th', 'something else')

        self.humanize_tester(test_list, result_list, 'ordinal')

    def test_intcomma(self):
        test_list = (100, 1000, 10123, 10311, 1000000, 1234567.25,
                     '100','1000','10123','10311','1000000','1234567.1234567')
        result_list = ('100', '1,000', '10,123', '10,311', '1,000,000','1,234,567.25',
                       '100', '1,000', '10,123', '10,311', '1,000,000','1,234,567.1234567')

        self.humanize_tester(test_list, result_list, 'intcomma')

    def test_intword(self):
        test_list = ('100', '1000000', '1200000', '1290000',
                     '1000000000','2000000000','6000000000000')
        result_list = ('100', '1.0 million', '1.2 million', '1.3 million',
                       '1.0 billion', '2.0 billion', '6.0 trillion')

        self.humanize_tester(test_list, result_list, 'intword')

    def test_apnumber(self):
        test_list = [str(x) for x in xrange(1,11)]
        result_list = ('one', 'two', 'three', 'four', 'five', 'six',
                       'seven', 'eight', 'nine', '10')

        self.humanize_tester(test_list, result_list, 'apnumber')

if __name__ == '__main__':
    unittest.main()
    
