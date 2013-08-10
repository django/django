from unittest import skipIf

from django import http
from django.conf import settings, global_settings
from django.contrib.messages import constants, utils, get_level, set_level
from django.contrib.messages.api import MessageFailure
from django.contrib.messages.storage import default_storage, base
from django.contrib.messages.storage.base import Message
from django.core.urlresolvers import reverse
from django.test.utils import override_settings
from django.utils.translation import ugettext_lazy


def skipUnlessAuthIsInstalled(func):
    return skipIf(
        'django.contrib.auth' not in settings.INSTALLED_APPS,
        "django.contrib.auth isn't installed")(func)


def add_level_messages(storage):
    """
    Adds 6 messages from different levels (including a custom one) to a storage
    instance.
    """
    storage.add(constants.INFO, 'A generic info message')
    storage.add(29, 'Some custom level')
    storage.add(constants.DEBUG, 'A debugging message', extra_tags='extra-tag')
    storage.add(constants.WARNING, 'A warning')
    storage.add(constants.ERROR, 'An error')
    storage.add(constants.SUCCESS, 'This was a triumph.')


class override_settings_tags(override_settings):
     def enable(self):
        super(override_settings_tags, self).enable()
        # LEVEL_TAGS is a constant defined in the
        # django.contrib.messages.storage.base module, so after changing
        # settings.MESSAGE_TAGS, we need to update that constant too.
        self.old_level_tags = base.LEVEL_TAGS
        base.LEVEL_TAGS = utils.get_level_tags()
     def disable(self):
        super(override_settings_tags, self).disable()
        base.LEVEL_TAGS = self.old_level_tags


class BaseTests(object):
    storage_class = default_storage
    urls = 'django.contrib.messages.tests.urls'
    levels = {
        'debug': constants.DEBUG,
        'info': constants.INFO,
        'success': constants.SUCCESS,
        'warning': constants.WARNING,
        'error': constants.ERROR,
    }

    def setUp(self):
        self.settings_override = override_settings_tags(
            TEMPLATE_DIRS   = (),
            TEMPLATE_CONTEXT_PROCESSORS = global_settings.TEMPLATE_CONTEXT_PROCESSORS,
            MESSAGE_TAGS    = '',
            MESSAGE_STORAGE = '%s.%s' % (self.storage_class.__module__,
                                         self.storage_class.__name__),
        )
        self.settings_override.enable()

    def tearDown(self):
        self.settings_override.disable()

    def get_request(self):
        return http.HttpRequest()

    def get_response(self):
        return http.HttpResponse()

    def get_storage(self, data=None):
        """
        Returns the storage backend, setting its loaded data to the ``data``
        argument.

        This method avoids the storage ``_get`` method from getting called so
        that other parts of the storage backend can be tested independent of
        the message retrieval logic.
        """
        storage = self.storage_class(self.get_request())
        storage._loaded_data = data or []
        return storage

    def test_add(self):
        storage = self.get_storage()
        self.assertFalse(storage.added_new)
        storage.add(constants.INFO, 'Test message 1')
        self.assertTrue(storage.added_new)
        storage.add(constants.INFO, 'Test message 2', extra_tags='tag')
        self.assertEqual(len(storage), 2)

    def test_add_lazy_translation(self):
        storage = self.get_storage()
        response = self.get_response()

        storage.add(constants.INFO, ugettext_lazy('lazy message'))
        storage.update(response)

        storing = self.stored_messages_count(storage, response)
        self.assertEqual(storing, 1)

    def test_no_update(self):
        storage = self.get_storage()
        response = self.get_response()
        storage.update(response)
        storing = self.stored_messages_count(storage, response)
        self.assertEqual(storing, 0)

    def test_add_update(self):
        storage = self.get_storage()
        response = self.get_response()

        storage.add(constants.INFO, 'Test message 1')
        storage.add(constants.INFO, 'Test message 1', extra_tags='tag')
        storage.update(response)

        storing = self.stored_messages_count(storage, response)
        self.assertEqual(storing, 2)

    def test_existing_add_read_update(self):
        storage = self.get_existing_storage()
        response = self.get_response()

        storage.add(constants.INFO, 'Test message 3')
        list(storage)   # Simulates a read
        storage.update(response)

        storing = self.stored_messages_count(storage, response)
        self.assertEqual(storing, 0)

    def test_existing_read_add_update(self):
        storage = self.get_existing_storage()
        response = self.get_response()

        list(storage)   # Simulates a read
        storage.add(constants.INFO, 'Test message 3')
        storage.update(response)

        storing = self.stored_messages_count(storage, response)
        self.assertEqual(storing, 1)

    @override_settings(MESSAGE_LEVEL=constants.DEBUG)
    def test_full_request_response_cycle(self):
        """
        With the message middleware enabled, tests that messages are properly
        stored and then retrieved across the full request/redirect/response
        cycle.
        """
        data = {
            'messages': ['Test message %d' % x for x in range(5)],
        }
        show_url = reverse('django.contrib.messages.tests.urls.show')
        for level in ('debug', 'info', 'success', 'warning', 'error'):
            add_url = reverse('django.contrib.messages.tests.urls.add',
                              args=(level,))
            response = self.client.post(add_url, data, follow=True)
            self.assertRedirects(response, show_url)
            self.assertTrue('messages' in response.context)
            messages = [Message(self.levels[level], msg) for msg in
                                                         data['messages']]
            self.assertEqual(list(response.context['messages']), messages)
            for msg in data['messages']:
                self.assertContains(response, msg)

    @override_settings(MESSAGE_LEVEL=constants.DEBUG)
    def test_with_template_response(self):
        data = {
            'messages': ['Test message %d' % x for x in range(5)],
        }
        show_url = reverse('django.contrib.messages.tests.urls.show_template_response')
        for level in self.levels.keys():
            add_url = reverse('django.contrib.messages.tests.urls.add_template_response',
                              args=(level,))
            response = self.client.post(add_url, data, follow=True)
            self.assertRedirects(response, show_url)
            self.assertTrue('messages' in response.context)
            for msg in data['messages']:
                self.assertContains(response, msg)

            # there shouldn't be any messages on second GET request
            response = self.client.get(show_url)
            for msg in data['messages']:
                self.assertNotContains(response, msg)

    @override_settings(MESSAGE_LEVEL=constants.DEBUG)
    def test_multiple_posts(self):
        """
        Tests that messages persist properly when multiple POSTs are made
        before a GET.
        """
        data = {
            'messages': ['Test message %d' % x for x in range(5)],
        }
        show_url = reverse('django.contrib.messages.tests.urls.show')
        messages = []
        for level in ('debug', 'info', 'success', 'warning', 'error'):
            messages.extend([Message(self.levels[level], msg) for msg in
                                                             data['messages']])
            add_url = reverse('django.contrib.messages.tests.urls.add',
                              args=(level,))
            self.client.post(add_url, data)
        response = self.client.get(show_url)
        self.assertTrue('messages' in response.context)
        self.assertEqual(list(response.context['messages']), messages)
        for msg in data['messages']:
            self.assertContains(response, msg)

    @override_settings(
        INSTALLED_APPS=filter(
            lambda app:app!='django.contrib.messages', settings.INSTALLED_APPS),
        MIDDLEWARE_CLASSES=filter(
            lambda m:'MessageMiddleware' not in m, settings.MIDDLEWARE_CLASSES),
        TEMPLATE_CONTEXT_PROCESSORS=filter(
            lambda p:'context_processors.messages' not in p,
                 settings.TEMPLATE_CONTEXT_PROCESSORS),
        MESSAGE_LEVEL=constants.DEBUG
    )
    def test_middleware_disabled(self):
        """
        Tests that, when the middleware is disabled, an exception is raised
        when one attempts to store a message.
        """
        data = {
            'messages': ['Test message %d' % x for x in range(5)],
        }
        show_url = reverse('django.contrib.messages.tests.urls.show')
        for level in ('debug', 'info', 'success', 'warning', 'error'):
            add_url = reverse('django.contrib.messages.tests.urls.add',
                              args=(level,))
            self.assertRaises(MessageFailure, self.client.post, add_url,
                              data, follow=True)

    @override_settings(
        INSTALLED_APPS=filter(
            lambda app:app!='django.contrib.messages', settings.INSTALLED_APPS),
        MIDDLEWARE_CLASSES=filter(
            lambda m:'MessageMiddleware' not in m, settings.MIDDLEWARE_CLASSES),
        TEMPLATE_CONTEXT_PROCESSORS=filter(
            lambda p:'context_processors.messages' not in p,
                 settings.TEMPLATE_CONTEXT_PROCESSORS),
        MESSAGE_LEVEL=constants.DEBUG
    )
    def test_middleware_disabled_fail_silently(self):
        """
        Tests that, when the middleware is disabled, an exception is not
        raised if 'fail_silently' = True
        """
        data = {
            'messages': ['Test message %d' % x for x in range(5)],
            'fail_silently': True,
        }
        show_url = reverse('django.contrib.messages.tests.urls.show')
        for level in ('debug', 'info', 'success', 'warning', 'error'):
            add_url = reverse('django.contrib.messages.tests.urls.add',
                              args=(level,))
            response = self.client.post(add_url, data, follow=True)
            self.assertRedirects(response, show_url)
            self.assertFalse('messages' in response.context)

    def stored_messages_count(self, storage, response):
        """
        Returns the number of messages being stored after a
        ``storage.update()`` call.
        """
        raise NotImplementedError('This method must be set by a subclass.')

    def test_get(self):
        raise NotImplementedError('This method must be set by a subclass.')

    def get_existing_storage(self):
        return self.get_storage([Message(constants.INFO, 'Test message 1'),
                                 Message(constants.INFO, 'Test message 2',
                                              extra_tags='tag')])

    def test_existing_read(self):
        """
        Tests that reading the existing storage doesn't cause the data to be
        lost.
        """
        storage = self.get_existing_storage()
        self.assertFalse(storage.used)
        # After iterating the storage engine directly, the used flag is set.
        data = list(storage)
        self.assertTrue(storage.used)
        # The data does not disappear because it has been iterated.
        self.assertEqual(data, list(storage))

    def test_existing_add(self):
        storage = self.get_existing_storage()
        self.assertFalse(storage.added_new)
        storage.add(constants.INFO, 'Test message 3')
        self.assertTrue(storage.added_new)

    def test_default_level(self):
        # get_level works even with no storage on the request.
        request = self.get_request()
        self.assertEqual(get_level(request), constants.INFO)

        # get_level returns the default level if it hasn't been set.
        storage = self.get_storage()
        request._messages = storage
        self.assertEqual(get_level(request), constants.INFO)

        # Only messages of sufficient level get recorded.
        add_level_messages(storage)
        self.assertEqual(len(storage), 5)

    def test_low_level(self):
        request = self.get_request()
        storage = self.storage_class(request)
        request._messages = storage

        self.assertTrue(set_level(request, 5))
        self.assertEqual(get_level(request), 5)

        add_level_messages(storage)
        self.assertEqual(len(storage), 6)

    def test_high_level(self):
        request = self.get_request()
        storage = self.storage_class(request)
        request._messages = storage

        self.assertTrue(set_level(request, 30))
        self.assertEqual(get_level(request), 30)

        add_level_messages(storage)
        self.assertEqual(len(storage), 2)

    @override_settings(MESSAGE_LEVEL=29)
    def test_settings_level(self):
        request = self.get_request()
        storage = self.storage_class(request)

        self.assertEqual(get_level(request), 29)

        add_level_messages(storage)
        self.assertEqual(len(storage), 3)

    def test_tags(self):
        storage = self.get_storage()
        storage.level = 0
        add_level_messages(storage)
        tags = [msg.tags for msg in storage]
        self.assertEqual(tags,
                         ['info', '', 'extra-tag debug', 'warning', 'error',
                          'success'])

    @override_settings_tags(MESSAGE_TAGS={
            constants.INFO: 'info',
            constants.DEBUG: '',
            constants.WARNING: '',
            constants.ERROR: 'bad',
            29: 'custom',
        }
    )
    def test_custom_tags(self):
        storage = self.get_storage()
        storage.level = 0
        add_level_messages(storage)
        tags = [msg.tags for msg in storage]
        self.assertEqual(tags,
                     ['info', 'custom', 'extra-tag', '', 'bad', 'success'])
