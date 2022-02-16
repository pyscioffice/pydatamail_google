import os
import base64
import email
import numpy as np
from tqdm import tqdm
from datetime import datetime
from PyPDF3 import PdfFileMerger
from email2pdf import (
    get_unique_version,
    get_input_email,
    handle_message_body,
    remove_invalid_urls,
    get_formatted_header_info,
    output_body_pdf,
    FatalException,
)


def convert_eml_to_pdf(input_file, output_file):
    output_file_name = get_unique_version(filename=output_file)

    with open(input_file, "r") as input_handle:
        input_data = input_handle.read()

    input_email = get_input_email(input_data)
    (payload, parts_already_used) = handle_message_body(
        args=None, input_email=input_email
    )

    payload = remove_invalid_urls(payload=payload)

    header_info = get_formatted_header_info(input_email=input_email)
    payload = header_info + payload
    output_body_pdf(
        input_email=input_email,
        payload=bytes(payload, "UTF-8"),
        output_file_name=output_file_name,
    )


def get_date(message_details):
    for message_detail in message_details["payload"]["headers"]:
        if message_detail["name"] == "Date":
            return datetime.strptime(
                message_detail["value"], "%a, %d %b %Y %H:%M:%S %z"
            )


def convert_eml_folder_to_pdf(folder_to_save_all_emails):
    eml_file_lst = []
    for root, dirs, files in os.walk(folder_to_save_all_emails, topdown=False):
        for f in files:
            if f.endswith(".eml"):
                eml_file_lst.append(os.path.join(root, os.path.splitext(f)[0]))
    for f in tqdm(eml_file_lst):
        try:
            convert_eml_to_pdf(input_file=f + ".eml", output_file=f + ".pdf")
        except FatalException:
            print(f)


def save_message_to_eml(messageraw, path_to_folder):
    msg_str = base64.urlsafe_b64decode(messageraw["raw"].encode("ASCII"))
    mime_msg = email.message_from_string(msg_str.decode())

    if not os.path.exists(path_to_folder):
        os.makedirs(path_to_folder)

    emlfile = os.path.join(path_to_folder, "email.eml")
    with open(emlfile, "w") as outfile:
        gen = email.generator.Generator(outfile)
        gen.flatten(mime_msg)


def merge_pdf(folder_to_save_all_emails, message_sort_dict, file_name="result.pdf"):
    pdf_file_lst = []
    for root, dirs, files in os.walk(folder_to_save_all_emails, topdown=False):
        for f in files:
            if f.endswith(".pdf"):
                pdf_file_lst.append(os.path.join(root, f))

    message_ids = list(message_sort_dict.keys())
    date_lst = list(message_sort_dict.values())
    message_ids_sorted = np.array(message_ids)[np.argsort(date_lst)]
    file_dict = {f.split("/")[1]: f for f in pdf_file_lst}
    pdf_file_sorted_lst = [
        file_dict[m] for m in message_ids_sorted if m in file_dict.keys()
    ]

    merger = PdfFileMerger()
    for pdf in tqdm(pdf_file_sorted_lst):
        merger.append(pdf)
    merger.write(file_name)
    merger.close()
