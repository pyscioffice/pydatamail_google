import os
import json
from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
from googleapiclient.discovery import build
from google_auth_oauthlib.flow import InstalledAppFlow
from pydatamail_google.base import GoogleDriveBase, GoogleMailBase


class Drive(GoogleDriveBase):
    def __init__(self, client_service_file=None, config_folder="~/.pydatamail"):
        """
        Google Drive class to manage files via the Google drive API directly from Python

        Args:
            client_service_file (str/ None): path to the credentials.json file
                                             typically "~/.pydatamail_google/credentials.json"
            config_folder (str): the folder for the configuration, typically "~/.pydatamail_google"
        """
        connect_dict = {
            "api_name": "drive",
            "api_version": "v3",
            "scopes": ["https://www.googleapis.com/auth/drive"],
        }
        self._config_path = _create_config_folder(config_folder=config_folder)
        if client_service_file is None:
            client_service_file = os.path.join(self._config_path, "credentials.json")

        super().__init__(
            _create_service(
                client_secret_file=client_service_file,
                api_name=connect_dict["api_name"],
                api_version=connect_dict["api_version"],
                scopes=connect_dict["scopes"],
                prefix="",
                working_dir=self._config_path,
            )
        )


class Gmail(GoogleMailBase):
    def __init__(
        self,
        client_service_file=None,
        userid="me",
        config_folder="~/.pydatamail",
        enable_google_drive=True,
    ):
        """
        Gmail class to manage Emails via the Gmail API directly from Python

        Args:
            client_service_file (str/ None): path to the credentials.json file
                                             typically "~/.pydatamail/credentials.json"
            userid (str): in most cases this should be simply "me"
            config_folder (str): the folder for the configuration, typically "~/.pydatamail"
        """
        connect_dict = {
            "api_name": "gmail",
            "api_version": "v1",
            "scopes": ["https://mail.google.com/"],
        }

        # Create config directory
        self._config_path = _create_config_folder(config_folder=config_folder)
        if client_service_file is None:
            client_service_file = os.path.join(self._config_path, "credentials.json")
        self._client_service_file = client_service_file

        # Read config file
        config_file = os.path.join(self._config_path, "config.json")
        if os.path.exists(config_file):
            with open(config_file) as f:
                self._config_dict = json.load(f)
        else:
            self._config_dict = {}

        # Initialise service
        google_mail_service = _create_service(
            client_secret_file=self._client_service_file,
            api_name=connect_dict["api_name"],
            api_version=connect_dict["api_version"],
            scopes=connect_dict["scopes"],
            prefix="",
            working_dir=self._config_path,
        )

        # Google drive
        if enable_google_drive:
            google_drive_service = Drive(client_service_file=self._client_service_file)
        else:
            google_drive_service = None

        # Initialize database
        if "database" in self._config_dict.keys():
            database = self._create_database(
                connection_str=self._config_dict["database"]
            )
        else:
            database = None

        super().__init__(
            google_mail_service=google_mail_service,
            database=database,
            google_drive_service=google_drive_service,
            userid=userid,
        )


def _create_service(
    client_secret_file, api_name, api_version, scopes, prefix="", working_dir=None
):
    cred = None
    if working_dir is None:
        working_dir = os.getcwd()
    token_dir = "token_files"
    json_file = f"token_{api_name}_{api_version}{prefix}.json"

    os.makedirs(os.path.join(working_dir, token_dir), exist_ok=True)
    token_file = os.path.join(working_dir, token_dir, json_file)
    if os.path.exists(token_file):
        cred = Credentials.from_authorized_user_file(token_file, scopes)

    if not cred or not cred.valid:
        if cred and cred.expired and cred.refresh_token:
            cred.refresh(Request())
        else:
            flow = InstalledAppFlow.from_client_secrets_file(client_secret_file, scopes)
            cred = flow.run_local_server()

        with open(os.path.join(working_dir, token_dir, json_file), "w") as token:
            token.write(cred.to_json())

    return build(api_name, api_version, credentials=cred)


def _create_config_folder(config_folder="~/.pydatamail_google"):
    config_path = os.path.abspath(os.path.expanduser(config_folder))
    os.makedirs(config_path, exist_ok=True)
    return config_path
