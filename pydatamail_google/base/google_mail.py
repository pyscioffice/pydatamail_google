import os
import json
import shutil
import warnings
from tqdm import tqdm
from pygmailsorter.google.mail import GoogleMailBase as GoogleMailSorter

try:
    from pydatamail_google.base.archive import (
        convert_eml_folder_to_pdf,
        get_date,
        save_message_to_eml,
        merge_pdf,
    )
except ImportError:
    warnings.warn("Archiving to Google Drive requires PyPDF3 and email2pdf2.")


class GoogleMailBase(GoogleMailSorter):
    def __init__(
        self,
        google_mail_service,
        database_email=None,
        database_ml=None,
        google_drive_service=None,
        user_id="me",
        db_user_id=1,
    ):
        super(GoogleMailBase).__init__(
            google_mail_service=google_mail_service,
            database_email=database_email,
            database_ml=database_ml,
            user_id=user_id,
            db_user_id=db_user_id,
        )
        self._drive = google_drive_service

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
            iterable=self._get_message_ids(message_lst=message_list_response),
            desc="Filter label by sender",
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
            elif task == "filter_label_by_machine_learning":
                self.update_database(quick=True, label_lst=[task_input])
                self.filter_label_by_machine_learning(
                    label=task_input, recalculate=True
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
        for email_message_id in tqdm(
            iterable=email_messages, desc="Save attachments of label"
        ):
            self._save_attachments_of_message(
                email_message_id=email_message_id,
                folder_id=folder_id,
                exclude_files_lst=files_lst,
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
            for emails in tqdm(
                iterable=all_message_in_label, desc="Save label to EML file"
            ):
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
