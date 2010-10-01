from django.test import TestCase


class ObjectListTest(TestCase):
    fixtures = ['testdata.json']

    def check_pagination(self, url, expected_status_code, object_count=None):
        response = self.client.get(url)
        self.assertEqual(response.status_code, expected_status_code)

        if object_count:
            self.assertEqual(response.context['is_paginated'], True)
            self.assertEqual(len(response.context['page_obj'].object_list),
                             object_count)

        return response

    def test_finds_pages(self):
        # Check page count doesn't start at 0.
        self.check_pagination('/views/object_list/page0/', 404)

        # Check basic pages.
        self.check_pagination('/views/object_list/page/', 200, 2)
        self.check_pagination('/views/object_list/page1/', 200, 2)
        self.check_pagination('/views/object_list/page2/', 200, 1)
        self.check_pagination('/views/object_list/page3/', 404)

        # Check the special "last" page.
        self.check_pagination('/views/object_list/pagelast/', 200, 1)
        self.check_pagination('/views/object_list/pagenotlast/', 404)

    def test_no_paginate_by(self):
        # Ensure that the view isn't paginated by default.
        url = '/views/object_list_no_paginate_by/page1/'
        response = self.check_pagination(url, 200)
        self.assertEqual(response.context['is_paginated'], False)
