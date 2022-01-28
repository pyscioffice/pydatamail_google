import os
import json
from tqdm import tqdm
from pygmailfilter.service import create_service, create_config_folder
from pygmailfilter.message import Message


class Gmail:
    def __init__(self, client_service_file=None, userid="me"):
        connect_dict = {
            "api_name": "gmail",
            "api_version": "v1",
            "scopes": ["https://mail.google.com/"]
        }
        self._config_path = create_config_folder(config_folder="~/.pygmailfilter")
        if client_service_file is None:
            client_service_file = os.path.join(self._config_path, "credentials.json")

        self._userid = userid
        self._service = create_service(
            client_secret_file=client_service_file,
            api_name=connect_dict["api_name"],
            api_version=connect_dict["api_version"],
            scopes=connect_dict["scopes"],
            prefix='',
            working_dir=self._config_path
        )
        self._label_dict = self._get_label_translate_dict()

    @property
    def labels(self):
        return list(self._label_dict.keys())

    def filter_label_by_sender(self, label, filter_dict_lst):
        message_list_response = self.search_email(
            query_string="",
            label_lst=[label]
        )

        for message_id in tqdm(self._get_message_ids(message_lst=message_list_response)):
            label_add = self._filter_message_by_sender(filter_dict_lst=filter_dict_lst, message_id=message_id)
            if label_add is not None:
                self._modify_message_labels(
                    message_id=message_id,
                    label_id_remove_lst=[label],
                    label_id_add_lst=[label_add]
                )

    def search_email(self, query_string="", label_lst=[]):
        label_ids = [self._label_dict[label] for label in label_lst]
        return self._get_messages(
            query_string=query_string,
            label_ids=label_ids
        )

    def remove_labels_from_emails(self, label_lst):
        label_convert_lst = [self._label_dict[label] for label in label_lst]
        for label in tqdm(label_convert_lst):
            message_list_response = self._get_messages(
                query_string="",
                label_ids=[label]
            )
            for message_id in tqdm(self._get_message_ids(message_lst=message_list_response)):
                self._modify_message_labels(
                    message_id=message_id,
                    label_id_remove_lst=[label]
                )

    def load_json_tasks(self, config_json=None):
        if config_json is None:
            config_json = os.path.join(self._config_path, "config.json")
        with open(config_json) as f:
            task_dict = json.load(f)
        for task, task_input in task_dict.items():
            if task == "remove_labels_from_emails":
                self.remove_labels_from_emails(
                    label_lst=task_input
                )
            elif task == "filter_label_by_sender":
                self.filter_label_by_sender(
                    label=task_input["label"],
                    filter_dict_lst=task_input["filter_dict_lst"]
                )
            else:
                raise ValueError("Task not recognized: ", task)

    def _get_message_detail(self, message_id, format="metadata", metadata_headers=[]):
        return self._service.users().messages().get(
            userId=self._userid,
            id=message_id,
            format=format,
            metadataHeaders=metadata_headers
        ).execute()

    def _filter_message_by_sender(self, filter_dict_lst, message_id):
        message = Message(self._get_message_detail(
            message_id=message_id,
            format="metadata",
            metadata_headers=[]
        ))
        for filter_dict in filter_dict_lst:
            if "from" in filter_dict.keys() and filter_dict["from"] in message.get_from():
                return self._label_dict[filter_dict["label"]]
            if "to" in filter_dict.keys() and filter_dict["to"] in message.get_to():
                return self._label_dict[filter_dict["label"]]
            if "subject" in filter_dict.keys() and filter_dict["subject"] in message.get_subject():
                return self._label_dict[filter_dict["label"]]
        return None

    def _modify_message_labels(self, message_id, label_id_remove_lst=[], label_id_add_lst=[]):
        body_dict = {}
        if len(label_id_remove_lst) > 0:
            body_dict["removeLabelIds"] = label_id_remove_lst
        if len(label_id_add_lst) > 0:
            body_dict["addLabelIds"] = label_id_add_lst
        if len(body_dict) > 0:
            self._service.users().messages().modify(
                userId=self._userid,
                id=message_id,
                body=body_dict
            ).execute()

    def _get_label_translate_dict(self):
        results = self._service.users().labels().list(
            userId=self._userid
        ).execute()
        labels = results.get('labels', [])
        return {label["name"]: label["id"] for label in labels}

    def _get_messages_page(self, label_ids, query_string, next_page_token=None):
        message_list_response = self._service.users().messages().list(
            userId=self._userid,
            labelIds=label_ids,
            q=query_string,
            pageToken=next_page_token
        ).execute()

        return [
            message_list_response.get("messages"),
            message_list_response.get("nextPageToken")
        ]

    def _get_messages(self, query_string="", label_ids=[]):
        message_items_lst, next_page_token = self._get_messages_page(
            label_ids=label_ids,
            query_string=query_string,
            next_page_token=None
        )

        while next_page_token:
            message_items, next_page_token = self._get_messages_page(
                label_ids=label_ids,
                query_string=query_string,
                next_page_token=None
            )
            message_items_lst.extend(message_items)

        if message_items_lst is None:
            return []
        else:
            return message_items_lst

    @staticmethod
    def _get_message_ids(message_lst):
        return [d['id'] for d in message_lst]
