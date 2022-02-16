import os
import json
import pandas
import shutil
import warnings
from tqdm import tqdm
from sqlalchemy import create_engine
from pydatamail_google.base.message import Message, get_email_dict
from pydatamail import DatabaseInterface

try:
    from pydatamail_google.base.archive import (
        convert_eml_folder_to_pdf,
        get_date,
        save_message_to_eml,
        merge_pdf,
    )
except ImportError:
    warnings.warn("Archiving to Google Drive requires PyPDF3 and email2pdf.")


class GoogleMailBase:
    def __init__(
        self, google_mail_service, database=None, google_drive_service=None, userid="me"
    ):
        self._service = google_mail_service
        self._db = database
        self._drive = google_drive_service
        self._userid = userid
        self._label_dict = self._get_label_translate_dict()

    @property
    def labels(self):
        return list(self._label_dict.keys())

    def filter_label_by_sender(self, label, filter_dict_lst):
        """
        Filter emails in a given email label by applying a list of email filters, only the first filter that matches is
        applied. A typical email filter list might look like this:
             [{"from": "my_email@provider.com", "label": "my_special_label"},
              {"to": "spam@google.com", "label": "another_email_label"},
              {"subject": "you won", "label": "success_story"}]
        At the current stage only one of the three fields "from", "to" or "subject" can be validated per filter and all
        filters are applied as "is in" rather than an exact match.

        Args:
            label (str): Email label as string not email label id.
            filter_dict_lst (list): List of filter rules with each filter rule represented by a dictionary
        """
        message_list_response = self.search_email(query_string="", label_lst=[label])

        for message_id in tqdm(
            self._get_message_ids(message_lst=message_list_response)
        ):
            label_add = self._filter_message_by_sender(
                filter_dict_lst=filter_dict_lst, message_id=message_id
            )
            if label_add is not None:
                self._modify_message_labels(
                    message_id=message_id,
                    label_id_remove_lst=[self._label_dict[label]],
                    label_id_add_lst=[label_add],
                )

    def update_database(self):
        """
        Update local email database
        """
        if self._db is not None:
            message_id_lst = self.search_email(only_message_ids=True)
            (
                new_messages_lst,
                message_label_updates_lst,
                deleted_messages_lst,
            ) = self._db.get_labels_to_update(message_id_lst=message_id_lst)
            self._db.mark_emails_as_deleted(message_id_lst=deleted_messages_lst)
            self._db.update_labels(
                message_id_lst=message_label_updates_lst,
                message_meta_lst=self.get_labels_for_emails(
                    message_id_lst=message_label_updates_lst
                ),
            )
            self._store_emails_in_database(new_messages_lst)

    def get_labels_for_email(self, message_id):
        """
        Get labels for email

        Args:
            message_id (str): email ID

        Returns:
            list: List of email labels
        """
        message_dict = self._get_message_detail(
            message_id=message_id, format="metadata", metadata_headers=["labelIds"]
        )
        if "labelIds" in message_dict.keys():
            return message_dict["labelIds"]
        else:
            return []

    def get_labels_for_emails(self, message_id_lst):
        """
        Get labels for a list of emails

        Args:
            message_id_lst (list): list of emails IDs

        Returns:
            list: Nested list of email labels for each email
        """
        return [
            self.get_labels_for_email(message_id=message_id)
            for message_id in message_id_lst
        ]

    def get_all_emails_in_database(self, include_deleted=False):
        """
        Get all emails stored in local database

        Args:
            include_deleted (bool): Flag to include deleted emails - default False

        Returns:
            pandas.DataFrame: With all emails and the corresponding information
        """
        return self._db.get_all_emails(include_deleted=include_deleted)

    def search_email(self, query_string="", label_lst=[], only_message_ids=False):
        """
        Search emails either by a specific query or optionally limit your search to a list of labels

        Args:
            query_string (str): query string to search for
            label_lst (list): list of labels to be searched
            only_message_ids (bool): return only the email IDs not the thread IDs - default: false

        Returns:
            list: list with email IDs and thread IDs of the messages which match the search
        """
        label_ids = [self._label_dict[label] for label in label_lst]
        message_id_lst = self._get_messages(
            query_string=query_string, label_ids=label_ids
        )
        if not only_message_ids:
            return message_id_lst
        else:
            return [d["id"] for d in message_id_lst]

    def remove_labels_from_emails(self, label_lst):
        """
        Remove a list of labels from all emails in Gmail. A typical application is removing the Gmail smart labels:
            label_lst=["CATEGORY_FORUMS", "CATEGORY_UPDATES", "CATEGORY_PROMOTIONS", "CATEGORY_SOCIAL"]

        Args:
            label_lst (list): list of labels
        """
        label_convert_lst = [self._label_dict[label] for label in label_lst]
        for label in tqdm(label_convert_lst):
            message_list_response = self._get_messages(
                query_string="", label_ids=[label]
            )
            for message_id in tqdm(
                self._get_message_ids(message_lst=message_list_response)
            ):
                self._modify_message_labels(
                    message_id=message_id, label_id_remove_lst=[label]
                )

    def load_json_tasks(self, config_json=None):
        """
        Execute tasks defined in the JSON configuration. If no config_json file is provide the default location is:
            "~/.pydatamail_google/config.json"

        Args:
            config_json (str/ None): path to the config_json file, default ~/.pydatamail_google/config.json
        """
        if config_json is None:
            task_dict = self._config_dict
        else:
            with open(config_json) as f:
                task_dict = json.load(f)
        for task, task_input in task_dict.items():
            if task == "remove_labels_from_emails":
                self.remove_labels_from_emails(label_lst=task_input)
            elif task == "filter_label_by_sender":
                self.filter_label_by_sender(
                    label=task_input["label"],
                    filter_dict_lst=task_input["filter_dict_lst"],
                )
            elif task != "database":
                raise ValueError("Task not recognized: ", task)

    def save_attachments_of_label(self, label, path):
        """
        Save all attachments of emails marked with a selected label to a specific folder on Google drive. This requires
        Google drive authorisation to be included in the authentication credentials.

        Args:
            label (str): label name to search for emails with attachments
            path (str): path inside google drive, for example "backup/emails". In this path a new subfolder for the
                        label is created.
        """
        if self._drive is None:
            raise ValueError("Google drive is not enabled.")

        folder_id = self._drive.get_path_id(path=path)
        files_lst = [d["name"] for d in self._drive.list_folder_content(folder_id)]
        query_string = "has:attachment"
        email_messages = self.search_email(
            query_string=query_string, label_lst=[label], only_message_ids=True
        )
        for email_message_id in tqdm(email_messages):
            self._save_attachments_of_message(
                email_message_id=email_message_id,
                folder_id=folder_id,
                exclude_files_lst=files_lst,
            )

    def download_messages_to_dataframe(self, message_id_lst):
        """
        Download a list of messages based on their email IDs and store the content in a pandas.DataFrame.

        Args:
            message_id_lst (list): list of emails IDs

        Returns:
            pandas.DataFrame: pandas.DataFrame which contains the rendered emails
        """
        return pandas.DataFrame(
            [
                self.get_email_dict(message_id=message_id)
                for message_id in tqdm(message_id_lst)
            ]
        )

    def backup_emails_to_drive(self, label_to_backup, path, file_name="emails.pdf"):
        """
        Backup Emails to Google Drive by converting all emails to pdf and store the attachments in a sub folder named
        attachments.

        Args:
            label_to_backup (str): Label to be backed up
            path (str): Google drive path to backup emails to
            file_name (str): file name for the pdf document
        """
        tmp_folder = "backup"
        tmp_file = "result.pdf"

        # Save attachments
        self.save_attachments_of_label(
            label=label_to_backup,
            path=os.path.join(path, label_to_backup, "attachments"),
        )

        # Merge emails to pdf
        all_message_in_label = self._save_label_to_eml(
            label_to_backup=label_to_backup, folder_to_save_all_emails=tmp_folder
        )
        convert_eml_folder_to_pdf(folder_to_save_all_emails=tmp_folder)
        message_sort_dict = {
            message_detail["id"]: get_date(
                message_details=self._get_message_detail(
                    message_id=message_detail["id"]
                )
            )
            for message_detail in all_message_in_label
        }
        merge_pdf(
            folder_to_save_all_emails=tmp_folder,
            message_sort_dict=message_sort_dict,
            file_name=tmp_file,
        )

        # Upload pdf to Google Drive
        if self._drive is None:
            raise ValueError("Google drive is not enabled.")

        folder_id = self._drive.get_path_id(path=os.path.join(path, label_to_backup))
        file_metadata = {"name": file_name, "parents": [folder_id]}
        self._drive.save_file(
            path_to_file=os.path.expanduser(tmp_file),
            file_metadata=file_metadata,
            file_mimetype="application/pdf",
        )

        # Clean up
        shutil.rmtree(tmp_folder)
        os.remove(tmp_file)

    def get_email_dict(self, message_id):
        """
        Get the content of a given message as dictionary

        Args:
            message_id (str):

        Returns:
            dict: Dictionary with the message content
        """
        return get_email_dict(
            message=self._get_message_detail(message_id=message_id, format="full")
        )

    def _save_attachments_of_message(
        self, email_message_id, folder_id, exclude_files_lst=[]
    ):
        message_detail = self._get_message_detail(
            message_id=email_message_id, format="full", metadata_headers=["parts"]
        )
        message_detail_payload = message_detail.get("payload")

        if "parts" in message_detail_payload:
            for msgPayload in message_detail_payload["parts"]:
                mime_type = msgPayload["mimeType"]
                file_name = msgPayload["filename"]
                body = msgPayload["body"]

                if file_name in exclude_files_lst:
                    continue
                elif "attachmentId" in body:
                    attachment_id = body["attachmentId"]

                    response = (
                        self._service.users()
                        .messages()
                        .attachments()
                        .get(userId="me", messageId=email_message_id, id=attachment_id)
                        .execute()
                    )

                    self._drive.save_gmail_attachment(
                        response=response,
                        mime_type=mime_type,
                        file_name=file_name,
                        folder_id=folder_id,
                    )

    def _save_label_to_eml(self, label_to_backup, folder_to_save_all_emails):
        all_message_in_label = self.search_email(label_lst=[label_to_backup])
        if not all_message_in_label:
            print("No email LM found.")
        else:
            for emails in tqdm(all_message_in_label):
                messageraw = (
                    self._service.users()
                    .messages()
                    .get(
                        userId="me", id=emails["id"], format="raw", metadataHeaders=None
                    )
                    .execute()
                )
                save_message_to_eml(
                    messageraw=messageraw,
                    path_to_folder=folder_to_save_all_emails + "/" + messageraw["id"],
                )

        return all_message_in_label

    def _get_message_detail(self, message_id, format="metadata", metadata_headers=[]):
        return (
            self._service.users()
            .messages()
            .get(
                userId=self._userid,
                id=message_id,
                format=format,
                metadataHeaders=metadata_headers,
            )
            .execute()
        )

    def _filter_message_by_sender(self, filter_dict_lst, message_id):
        message = Message(
            self._get_message_detail(
                message_id=message_id, format="metadata", metadata_headers=[]
            )
        )
        for filter_dict in filter_dict_lst:
            message_from = message.get_from()
            message_to = message.get_to()
            message_subject = message.get_subject()
            if (
                "from" in filter_dict.keys()
                and message_from is not None
                and filter_dict["from"] in message_from
            ):
                return self._label_dict[filter_dict["label"]]
            if (
                "to" in filter_dict.keys()
                and message_to is not None
                and filter_dict["to"] in message_to
            ):
                return self._label_dict[filter_dict["label"]]
            if (
                "subject" in filter_dict.keys()
                and message_subject is not None
                and filter_dict["subject"] in message_subject
            ):
                return self._label_dict[filter_dict["label"]]
        return None

    def _modify_message_labels(
        self, message_id, label_id_remove_lst=[], label_id_add_lst=[]
    ):
        body_dict = {}
        if len(label_id_remove_lst) > 0:
            body_dict["removeLabelIds"] = label_id_remove_lst
        if len(label_id_add_lst) > 0:
            body_dict["addLabelIds"] = label_id_add_lst
        if len(body_dict) > 0:
            self._service.users().messages().modify(
                userId=self._userid, id=message_id, body=body_dict
            ).execute()

    def _get_label_translate_dict(self):
        results = self._service.users().labels().list(userId=self._userid).execute()
        labels = results.get("labels", [])
        return {label["name"]: label["id"] for label in labels}

    def _get_messages_page(self, label_ids, query_string, next_page_token=None):
        message_list_response = (
            self._service.users()
            .messages()
            .list(
                userId=self._userid,
                labelIds=label_ids,
                q=query_string,
                pageToken=next_page_token,
            )
            .execute()
        )

        return [
            message_list_response.get("messages"),
            message_list_response.get("nextPageToken"),
        ]

    def _get_messages(self, query_string="", label_ids=[]):
        message_items_lst, next_page_token = self._get_messages_page(
            label_ids=label_ids, query_string=query_string, next_page_token=None
        )

        while next_page_token:
            message_items, next_page_token = self._get_messages_page(
                label_ids=label_ids,
                query_string=query_string,
                next_page_token=next_page_token,
            )
            message_items_lst.extend(message_items)

        if message_items_lst is None:
            return []
        else:
            return message_items_lst

    def _store_emails_in_database(self, message_id_lst):
        df = self.download_messages_to_dataframe(message_id_lst=message_id_lst)
        if len(df) > 0:
            self._db.store_dataframe(df=df)

    @staticmethod
    def _get_message_ids(message_lst):
        return [d["id"] for d in message_lst]

    @classmethod
    def create_database(cls, connection_str):
        return DatabaseInterface(engine=create_engine(connection_str))
