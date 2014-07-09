from django.core.files.uploadedfile import UploadedFile
from django.utils.datastructures import MultiValueDict
from django.utils.functional import lazy_property
from django.utils import six

from django.contrib.formtools.wizard.storage.exceptions import NoFileStorageConfigured


class BaseStorage(object):
    step_key = 'step'
    step_data_key = 'step_data'
    step_files_key = 'step_files'
    extra_data_key = 'extra_data'

    def __init__(self, prefix, request=None, file_storage=None):
        self.prefix = 'wizard_%s' % prefix
        self.request = request
        self.file_storage = file_storage
        self._files = {}
        self._tmp_files = []

    def init_data(self):
        self.data = {
            self.step_key: None,
            self.step_data_key: {},
            self.step_files_key: {},
            self.extra_data_key: {},
        }

    def reset(self):
        # Store unused temporary file names in order to delete them
        # at the end of the response cycle through a callback attached in
        # `update_response`.
        wizard_files = self.data[self.step_files_key]
        for step_files in six.itervalues(wizard_files):
            for step_file in six.itervalues(step_files):
                self._tmp_files.append(step_file['tmp_name'])
        self.init_data()

    def _get_current_step(self):
        return self.data[self.step_key]

    def _set_current_step(self, step):
        self.data[self.step_key] = step

    current_step = lazy_property(_get_current_step, _set_current_step)

    def _get_extra_data(self):
        return self.data[self.extra_data_key]

    def _set_extra_data(self, extra_data):
        self.data[self.extra_data_key] = extra_data

    extra_data = lazy_property(_get_extra_data, _set_extra_data)

    def get_step_data(self, step):
        # When reading the serialized data, upconvert it to a MultiValueDict,
        # some serializers (json) don't preserve the type of the object.
        values = self.data[self.step_data_key].get(step, None)
        if values is not None:
            values = MultiValueDict(values)
        return values

    def set_step_data(self, step, cleaned_data):
        # If the value is a MultiValueDict, convert it to a regular dict of the
        # underlying contents.  Some serializers call the public API on it (as
        # opposed to the underlying dict methods), in which case the content
        # can be truncated (__getitem__ returns only the first item).
        if isinstance(cleaned_data, MultiValueDict):
            cleaned_data = dict(cleaned_data.lists())
        self.data[self.step_data_key][step] = cleaned_data

    @property
    def current_step_data(self):
        return self.get_step_data(self.current_step)

    def get_step_files(self, step):
        wizard_files = self.data[self.step_files_key].get(step, {})

        if wizard_files and not self.file_storage:
            raise NoFileStorageConfigured(
                "You need to define 'file_storage' in your "
                "wizard view in order to handle file uploads.")

        files = {}
        for field, field_dict in six.iteritems(wizard_files):
            field_dict = field_dict.copy()
            tmp_name = field_dict.pop('tmp_name')
            if (step, field) not in self._files:
                self._files[(step, field)] = UploadedFile(
                    file=self.file_storage.open(tmp_name), **field_dict)
            files[field] = self._files[(step, field)]
        return files or None

    def set_step_files(self, step, files):
        if files and not self.file_storage:
            raise NoFileStorageConfigured(
                "You need to define 'file_storage' in your "
                "wizard view in order to handle file uploads.")

        if step not in self.data[self.step_files_key]:
            self.data[self.step_files_key][step] = {}

        for field, field_file in six.iteritems(files or {}):
            tmp_filename = self.file_storage.save(field_file.name, field_file)
            file_dict = {
                'tmp_name': tmp_filename,
                'name': field_file.name,
                'content_type': field_file.content_type,
                'size': field_file.size,
                'charset': field_file.charset
            }
            self.data[self.step_files_key][step][field] = file_dict

    @property
    def current_step_files(self):
        return self.get_step_files(self.current_step)

    def update_response(self, response):
        def post_render_callback(response):
            for file in self._files.values():
                if not file.closed:
                    file.close()
            for tmp_file in self._tmp_files:
                self.file_storage.delete(tmp_file)

        if hasattr(response, 'render'):
            response.add_post_render_callback(post_render_callback)
        else:
            post_render_callback(response)
