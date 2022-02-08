import os
import json
from tqdm import tqdm
from pygmailfilter.service import create_service, create_config_folder
from pygmailfilter.message import Message
from pygmailfilter.drive import Drive


class Gmail:
    def __init__(
        self, client_service_file=None, userid="me", config_folder="~/.pygmailfilter"
    ):
        """
        Gmail class to manage Emails via the Gmail API directly from Python

        Args:
            client_service_file (str/ None): path to the credentials.json file
                                             typically "~/.pygmailfilter/credentials.json"
            userid (str): in most cases this should be simply "me"
            config_folder (str): the folder for the configuration, typically "~/.pygmailfilter"
        """
        connect_dict = {
            "api_name": "gmail",
            "api_version": "v1",
            "scopes": ["https://mail.google.com/"],
        }
        self._config_path = create_config_folder(config_folder=config_folder)
        if client_service_file is None:
            client_service_file = os.path.join(self._config_path, "credentials.json")

        self._client_service_file = client_service_file
        self._userid = userid
        self._service = create_service(
            client_secret_file=self._client_service_file,
            api_name=connect_dict["api_name"],
            api_version=connect_dict["api_version"],
            scopes=connect_dict["scopes"],
            prefix="",
            working_dir=self._config_path,
        )
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

    def search_email(self, query_string="", label_lst=[]):
        """
        Search emails either by a specific query or optionally limit your search to a list of labels

        Args:
            query_string: query string to search for
            label_lst (list): list of labels to be searched

        Returns:
            list: list with email IDs and thread IDs of the messages which match the search
        """
        label_ids = [self._label_dict[label] for label in label_lst]
        return self._get_messages(query_string=query_string, label_ids=label_ids)

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
            "~/.pygmailfilter/config.json"

        Args:
            config_json (str/ None): path to the config_json file, default ~/.pygmailfilter/config.json
        """
        if config_json is None:
            config_json = os.path.join(self._config_path, "config.json")
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
            else:
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
        drive = Drive(client_service_file=self._client_service_file)
        folder_id = drive.get_path_id(path=path)
        files_lst = [d["name"] for d in drive.list_folder_content(folder_id)]
        query_string = "has:attachment"
        email_messages = self.search_email(query_string=query_string, label_lst=[label])
        for email_message in tqdm(email_messages):
            self._save_attachments_of_message(
                drive_service=drive,
                email_message=email_message,
                folder_id=folder_id,
                exclude_files_lst=files_lst,
            )

    def _save_attachments_of_message(
        self, drive_service, email_message, folder_id, exclude_files_lst=[]
    ):
        message_detail = self._get_message_detail(
            message_id=email_message["id"], format="full", metadata_headers=["parts"]
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
                        .get(
                            userId="me", messageId=email_message["id"], id=attachment_id
                        )
                        .execute()
                    )

                    drive_service.save_gmail_attachment(
                        response=response,
                        mime_type=mime_type,
                        file_name=file_name,
                        folder_id=folder_id,
                    )

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
                label_ids=label_ids, query_string=query_string, next_page_token=None
            )
            message_items_lst.extend(message_items)

        if message_items_lst is None:
            return []
        else:
            return message_items_lst

    @staticmethod
    def _get_message_ids(message_lst):
        return [d["id"] for d in message_lst]
