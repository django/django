from django.test import TestCase
from django.core import management
from django.utils.six import StringIO
from django.core.management import color


class TestSqlIndexesTestCase(TestCase):
    
    def _call_command(self, app):
        new_io = StringIO()
        
        kwargs = {
            'stdout': new_io,
            'stderr': new_io,
        }
        
        management.call_command('sqlindexes', app, **kwargs)

        return new_io

    def _statements_including(self, statements, key):
        return [i for i in statements if key in i]

    def setUp(self):
        # need to force the output not to use ANSI color
        self.old_supports_color = color.supports_color
        color.supports_color = lambda: False

    def tearDown(self):
        # need to make sure that we replace the new supports_color()
        # method with the original one
        color.supports_color = self.old_supports_color

    def test_user_defined_indexes(self):
        output = self._call_command('management_commands')
        output = output.getvalue()
        create_statements = [stmt for stmt in output.split('\n') if 'management_commands' in stmt]

        # make sure we have 2 index creations for Post.comments
        num_post_comments_indexes = len(self._statements_including(create_statements, 'management_commands_post_comments'))
        self.assertEqual(num_post_comments_indexes, 2)

        # make sure we have 1 user-defined index creation for UserPost.uuid
        num_user_indexes = len(self._statements_including(create_statements, 'management_commands_userpost'))
        self.assertEqual(num_user_indexes, 1)
