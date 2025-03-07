from __future__ import unicode_literals
# coding: utf-8

import os
import time
import datetime
import warnings
import mimetypes

from django.core.files.storage import default_storage
from django.db.models.fields.files import FieldFile
from django.utils.encoding import smart_str
from django.utils.functional import cached_property

try:
    from django.utils.encoding import smart_text
except ImportError:
    # Backward compatibility for Py2 and Django < 1.5
    from django.utils.encoding import smart_unicode as smart_text

from filebrowser_safe.functions import get_file_type, path_strip, get_directory


class FileObjectAPI(object):
    """ A mixin class providing file properties. """
    def __init__(self, path, is_folder=None):
        self._is_folder = is_folder
        self.head = os.path.dirname(path)
        self.filename = os.path.basename(path)
        self.filename_lower = self.filename.lower()
        self.filename_root, self.extension = os.path.splitext(self.filename)
        self.mimetype = mimetypes.guess_type(self.filename)

    def __str__(self):
        return smart_str(self.path)

    def __unicode__(self):
        return smart_text(self.path)

    def __repr__(self):
        return smart_str("<%s: %s>" % (
            self.__class__.__name__, self or "None"))

    def __len__(self):
        return len(self.path)

    # GENERAL ATTRIBUTES

    @cached_property
    def filetype(self):
        if self.is_folder:
            return 'Folder'
        return get_file_type(self.filename)

    @cached_property
    def filesize(self):
        if self.exists:
            return default_storage.size(self.path)
        return None

    @cached_property
    def date(self):
        if self.exists:
            return time.mktime(
                default_storage.get_modified_time(self.path).timetuple())
        return None

    @property
    def datetime(self):
        if self.date:
            return datetime.datetime.fromtimestamp(self.date)
        return None

    @cached_property
    def exists(self):
        return default_storage.exists(self.path)

    # PATH/URL ATTRIBUTES

    @property
    def path_relative_directory(self):
        """ path relative to the path returned by get_directory() """
        return path_strip(self.path, get_directory()).lstrip("/")

    # FOLDER ATTRIBUTES

    @property
    def directory(self):
        return path_strip(self.path, get_directory())

    @property
    def folder(self):
        return os.path.dirname(
            path_strip(os.path.join(self.head, ''), get_directory()))

    @cached_property
    def is_folder(self):
        if self._is_folder is not None:
            return self._is_folder
        return default_storage.isdir(self.path)

    @property
    def is_empty(self):
        if self.is_folder:
            try:
                dirs, files = default_storage.listdir(self.path)
            except UnicodeDecodeError:
                from mezzanine.core.exceptions import FileSystemEncodingChanged
                raise FileSystemEncodingChanged()
            if not dirs and not files:
                return True
        return False


class FileObject(FileObjectAPI):
    """
    The FileObject represents a file (or directory) on the server.

    An example::

        from filebrowser.base import FileObject

        fileobject = FileObject(path)

    where path is a relative path to a storage location.
    """
    def __init__(self, path, *args, **kwargs):
        self.path = path
        super(FileObject, self).__init__(path, *args, **kwargs)

    @property
    def name(self):
        return self.path

    @property
    def url(self):
        return default_storage.url(self.path)


class FieldFileObject(FieldFile, FileObjectAPI):
    """
    Returned when a FileBrowseField is accessed on a model instance.

    - Implements the FieldFile API so FileBrowseField can act as substitute for
    django's built-in FileField.
    - Implements the FileObject API for historical reasons.
    """
    def __init__(self, instance, field, path):
        FieldFile.__init__(self, instance, field, path)
        FileObjectAPI.__init__(self, path or '')

    def delete(self, **kwargs):
        if self.is_folder:
            default_storage.rmtree(self.path)
        else:
            super(FieldFileObject, self).delete(**kwargs)

    @property
    def path(self):
        warnings.warn(
            "In future versions of filebrowser-safe, the `path` property will "
            "be absolute. To continue getting the same behavior please use "
            "the `name` property instead.", FutureWarning, stacklevel=2)
        return self.name
