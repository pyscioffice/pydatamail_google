import io
import base64
from googleapiclient.http import MediaIoBaseUpload, MediaFileUpload


class GoogleDriveBase:
    def __init__(self, service):
        self._service = service

    def get_path_id(self, path):
        parent_folder_id = None
        for p in path.split("/"):
            parent_folder_id = self.get_folder_id(
                folder_name=p, parent_folder=parent_folder_id
            )
        return parent_folder_id

    def create_folder(self, folder_name, parent_folder=[]):
        file_metadata = {
            "name": folder_name,
            "parents": parent_folder,
            "mimeType": "application/vnd.google-apps.folder",
        }

        file = self._service.files().create(body=file_metadata, fields="id").execute()
        return file

    def list_folder_content(self, folder=None):
        if folder is None:
            folder = "root"
        query = "'" + folder + "' in parents"
        files_items_lst, next_page_token = self._get_files_page(
            query=query, next_page_token=None
        )

        while next_page_token:
            files_items, next_page_token = self._get_files_page(
                query=query, next_page_token=next_page_token
            )
            files_items_lst.extend(files_items)

        if files_items_lst is None:
            return []
        else:
            return files_items_lst

    def get_folder_id(self, folder_name, parent_folder=None):
        folder_lst = self.list_folder_content(folder=parent_folder)
        lst = [d["id"] for d in folder_lst if d["name"] == folder_name]
        if len(lst) > 0:
            return lst[0]
        else:
            if parent_folder is None:
                parent_folder_lst = []
            else:
                parent_folder_lst = [parent_folder]
            folder = self.create_folder(
                folder_name=folder_name, parent_folder=parent_folder_lst
            )
            return folder["id"]

    def save_gmail_attachment(self, response, mime_type, file_name, folder_id):
        file_data = base64.urlsafe_b64decode(response.get("data").encode("UTF-8"))

        fh = io.BytesIO(file_data)

        file_metadata = {"name": file_name, "parents": [folder_id]}

        media_body = MediaIoBaseUpload(
            fh, mimetype=mime_type, chunksize=1024 * 1024, resumable=True
        )

        self._service.files().create(
            body=file_metadata, media_body=media_body, fields="id"
        ).execute()

    def save_file(self, path_to_file, file_metadata, file_mimetype="*/*"):
        media = MediaFileUpload(path_to_file, mimetype=file_mimetype)
        file = (
            self._service.files()
            .create(body=file_metadata, media_body=media, fields="id")
            .execute()
        )
        return file.get("id")

    def _get_files_page(self, query, next_page_token=None):
        response = (
            self._service.files()
            .list(
                q=query,
                pageSize=100,
                spaces="drive",
                corpora="user",
                fields=f"nextPageToken, files(id, name, parents, mimeType)",
                pageToken=next_page_token,
            )
            .execute()
        )
        return [
            response.get("files"),
            response.get("nextPageToken"),
        ]
