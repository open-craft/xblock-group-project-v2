import mimetypes

class UploadFile(object):

    file_name = None
    file_url = None

    def __init__(self, file, submission_id, project_context):#group_id, user_id, project_api)

        self.file = file
        self.mimetype = mimetypes.guess_type(self.file.name)[0]

        self.submission_id = submission_id
        self.group_id = project_context["group_id"]
        self.user_id = project_context["user_id"]
        self.project_api = project_context["project_api"]

    def save_file(self):
        # Simple file write to disk
        file_url = "{}_{}_{}".format(self.group_id, self.user_id, self.file.name)
        with open(file_url, 'wb') as temp_file:
            for chunk in self.file.chunks():
                temp_file.write(chunk)

        self.file_url = file_url

    def submit(self):
        submit_hash = {
            "document_id": self.submission_id,
            "document_url": self.file_url,
            "document_mime_type": self.mimetype,
            "user": self.user_id,
            "workgroup": self.group_id,
        }
        self.project_api.create_submission(submit_hash)