import io
import os
import base64
from googleapiclient.http import MediaIoBaseUpload
from pygmailfilter.service import create_service, create_config_folder


class Drive:
    def __init__(self, client_service_file=None):
        connect_dict = {
            "api_name": "drive",
            "api_version": "v3",
            "scopes": ["https://www.googleapis.com/auth/drive"]
        }
        self._config_path = create_config_folder(config_folder="~/.pygmailfilter")
        if client_service_file is None:
            client_service_file = os.path.join(self._config_path, "credentials.json")

        self._service = create_service(
            client_secret_file=client_service_file,
            api_name=connect_dict["api_name"],
            api_version=connect_dict["api_version"],
            scopes=connect_dict["scopes"],
            prefix="",
            working_dir=self._config_path,
        )

    def create_folder(self, folder_name, parent_folder=[]):
        file_metadata = {
            "name": folder_name,
            "parents": parent_folder,
            "mimeType": "application/vnd.google-apps.folder"
        }

        file = self._service.files().create(
            body=file_metadata,
            fields="id"
        ).execute()
        return file

    def get_folder_id(self, folder_name, parent_folder=None):
        if parent_folder is None:
            parent_folder = "root"
        response = self._service.files().list(
            q="'" + parent_folder + "' in parents",
            pageSize=100,
            spaces='drive',
            corpora='user',
            fields=f'nextPageToken, files(id, name, parents, mimeType)',
            pageToken=None
        ).execute()
        lst = [d["id"] for d in response["files"] if d["name"] == folder_name]
        if len(lst) > 0:
            return lst[0]
        else:
            if parent_folder == "root":
                parent_folder_lst = []
            else:
                parent_folder_lst = [parent_folder]
            folder = self.create_folder(
                folder_name=folder_name,
                parent_folder=parent_folder_lst
            )
            return folder["id"]

    def save_gmail_attachment(self, response, mime_type, file_name, folder_id):
        file_data = base64.urlsafe_b64decode(
            response.get("data").encode("UTF-8")
        )

        fh = io.BytesIO(file_data)

        file_metadata = {
            "name": file_name,
            "parents": [folder_id]
        }

        media_body = MediaIoBaseUpload(
            fh,
            mimetype=mime_type,
            chunksize=1024 * 1024,
            resumable=True
        )

        self._service.files().create(
            body=file_metadata,
            media_body=media_body,
            fields="id"
        ).execute()
