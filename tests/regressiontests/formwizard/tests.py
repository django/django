import re
from django import forms
from django.test import TestCase

class FormWizardWithNullBooleanField(TestCase):
    urls = 'regressiontests.formwizard.urls'

    input_re = re.compile('name="([^"]+)" value="([^"]+)"')

    wizard_url = '/wiz/'
    wizard_step_data = (
        {
            '0-name': 'Pony',
            '0-thirsty': '2',
        },
        {
            '1-address1': '123 Main St',
            '1-address2': 'Djangoland',
        },
        {
            '2-random_crap': 'blah blah',
        }
    )

    def grabFieldData(self, response):
        """
        Pull the appropriate field data from the context to pass to the next wizard step
        """
        previous_fields = response.context['previous_fields']
        fields = {'wizard_step': response.context['step0']}
        
        def grab(m):
            fields[m.group(1)] = m.group(2)
            return ''
        
        self.input_re.sub(grab, previous_fields)
        return fields

    def checkWizardStep(self, response, step_no):
        """
        Helper function to test each step of the wizard
        - Make sure the call succeeded
        - Make sure response is the proper step number
        - return the result from the post for the next step
        """
        step_count = len(self.wizard_step_data)

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'Step %d of %d' % (step_no, step_count))

        data = self.grabFieldData(response)
        data.update(self.wizard_step_data[step_no - 1])

        return self.client.post(self.wizard_url, data)
        
    def testWizard(self):
        response = self.client.get(self.wizard_url)
        for step_no in range(1, len(self.wizard_step_data) + 1):
            response = self.checkWizardStep(response, step_no)
