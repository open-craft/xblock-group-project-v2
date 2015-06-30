import logging
import mimetypes
import hashlib
from lazy.lazy import lazy

from django.core.files import File
from django.core.files.storage import default_storage
from django.conf import settings


log = logging.getLogger(__name__)  # pylint: disable=invalid-name


class UploadFile(object):
    _sha1_hash = None

    def __init__(self, file_stream, submission_id, project_context):  # group_id, user_id, project_api)

        self.file = file_stream
        self.mimetype = mimetypes.guess_type(self.file.name)[0]

        self.submission_id = submission_id
        self.group_id = project_context["group_id"]
        self.user_id = project_context["user_id"]
        self.project_api = project_context["project_api"]
        self.course_id = project_context["course_id"]

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
            location = default_storage.url(path)
        except NotImplementedError:
            location = "file:///{}/{}".format(settings.BASE_DIR, default_storage.path(path))

        return location

    @property
    def file_storage_path(self):
        return "group_work/{}/{}/{}".format(self.group_id, self.sha1, self.file.name)

    def save_file(self):
        path = self.file_storage_path
        if not default_storage.exists(path):
            log.debug("Storing to %s", path)
            default_storage.save(path, File(self.file))
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
