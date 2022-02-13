import os
from google_auth_oauthlib.flow import InstalledAppFlow
from googleapiclient.discovery import build
from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials


def create_service(
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


def create_config_folder(config_folder="~/.pydatamail_google"):
    config_path = os.path.abspath(os.path.expanduser(config_folder))
    os.makedirs(config_path, exist_ok=True)
    return config_path
