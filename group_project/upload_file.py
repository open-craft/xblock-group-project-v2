import mimetypes
import hashlib

from django.core.files import File
from django.core.files.storage import default_storage

from django.conf import settings

TRACE = True

class UploadFile(object):

    _sha1_hash = None

    def __init__(self, file, submission_id, project_context):#group_id, user_id, project_api)

        self.file = file
        self.mimetype = mimetypes.guess_type(self.file.name)[0]

        self.submission_id = submission_id
        self.group_id = project_context["group_id"]
        self.user_id = project_context["user_id"]
        self.project_api = project_context["project_api"]
        self.course_id = project_context["course_id"]

    @property
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
        location = None
        path = self._file_storage_path()

        try:
            location = default_storage.url(path)
        except NotImplementedError:
            location = "file:///{}/{}".format(settings.BASE_DIR, default_storage.path(path))

        return location

    def _file_storage_path(self):
        return "group_work/{}/{}/{}".format(self.group_id, self.sha1, self.file.name)

    def save_file(self):
        path = self._file_storage_path()
        if not default_storage.exists(path):
            if TRACE:
                print "Storing to {}".format(path)
            default_storage.save(path, File(self.file))
            if TRACE:
                print "Successfully stored file to {}".format(path)
        elif TRACE:
            print "File already stored at {}".format(path)

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
