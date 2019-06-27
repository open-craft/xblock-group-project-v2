import logging
import mimetypes
import hashlib
from lazy.lazy import lazy

from django.core.files import File
from django.core.files.storage import default_storage
from django.conf import settings

from group_project_v2.utils import PrivateMediaStorage


log = logging.getLogger(__name__)


class UploadFile(object):
    _sha1_hash = None

    def __init__(self, file_stream, submission_id, project_context):

        self.file = file_stream
        self.mimetype = mimetypes.guess_type(self.file.name)[0]

        self.submission_id = submission_id
        self.project_context = project_context

    def _get_project_context_key(self, key):
        return self.project_context[key]

    @property
    def user_id(self):
        return self._get_project_context_key("user_id")

    @property
    def group_id(self):
        return self._get_project_context_key("group_id")

    @property
    def course_id(self):
        return self._get_project_context_key("course_id")

    @property
    def project_api(self):
        return self._get_project_context_key("project_api")

    @lazy
    def sha1(self):
        if self._sha1_hash is None:
            self.file.seek(0)

            hash_sha1 = hashlib.sha1()
            # Can read chunks from uploaded file
            for chunk in self.file.chunks():
                hash_sha1.update(chunk)

            self._sha1_hash = hash_sha1.hexdigest()

            self.file.seek(0)

        return self._sha1_hash

    @property
    def file_url(self):
        path = self.file_storage_path

        try:
            location = self.storage.url(path)
        except NotImplementedError:
            location = "file:///{}/{}".format(settings.BASE_DIR, default_storage.path(path))

        return location

    @property
    def file_storage_path(self):
        return "group_work/{}/{}/{}".format(self.group_id, self.sha1, self.file.name)

    @property
    def storage(self):
        """
        Return private storage if default is s3
        """
        if settings.DEFAULT_FILE_STORAGE == 'storages.backends.s3boto.S3BotoStorage':
            return PrivateMediaStorage()

        return default_storage

    def save_file(self):
        path = self.file_storage_path

        if not self.storage.exists(path):
            log.debug("Storing to %s", path)
            self.storage.save(path, File(self.file))
            log.debug("Successfully stored file to %s", path)
        else:
            log.debug("File already stored at %s", path)

    def submit(self):
        submit_hash = {
            "document_id": self.submission_id,
            "document_url": self.file_url,
            "document_filename": self.file.name,
            "document_mime_type": self.mimetype,
            "user": self.user_id,
            "workgroup": self.group_id,
        }
        self.project_api.create_submission(submit_hash)
