import base64
from datetime import datetime
from html.parser import HTMLParser
from io import StringIO


# https://stackoverflow.com/questions/753052/strip-html-from-strings-in-python
class MLStripper(HTMLParser):
    def __init__(self):
        super().__init__()
        self.reset()
        self.strict = False
        self.convert_charrefs = True
        self.text = StringIO()

    def handle_data(self, d):
        self.text.write(d)

    def get_data(self):
        return self.text.getvalue()


def get_email_dict(message):
    return Message(message_dict=message).to_dict()


class Message:
    def __init__(self, message_dict):
        self._message_dict = message_dict

    def get_from(self):
        return self.get_header_field_from_message(field="From")

    def get_to(self):
        return self.get_header_field_from_message(field="To")

    def get_label_ids(self):
        if "labelIds" in self._message_dict.keys():
            return self._message_dict["labelIds"]
        else:
            return []

    def get_subject(self):
        return self.get_header_field_from_message(field="Subject")

    def get_date(self):
        return datetime.strptime(
            self.get_header_field_from_message(field="Date"), "%a, %d %b %Y %H:%M:%S %z"
        )

    def get_content(self):
        if "parts" in self._message_dict["payload"].keys():
            return self._get_parts_content(
                message_parts=self._message_dict["payload"]["parts"]
            )
        else:
            return self._get_parts_content(
                message_parts=[self._message_dict["payload"]]
            )

    def get_thread_id(self):
        return self._message_dict["threadId"]

    def get_email_id(self):
        return self._message_dict["id"]

    def get_header_field_from_message(self, field):
        lst = [
            entry["value"]
            for entry in self._message_dict["payload"]["headers"]
            if entry["name"] == field
        ]
        if len(lst) > 0:
            return lst[0]
        else:
            return None

    def to_dict(self):
        return {
            "id": self.get_email_id(),
            "thread_id": self.get_thread_id(),
            "label_ids": self.get_label_ids(),
            "to": self.get_to(),
            "from": self.get_from(),
            "subject": self.get_subject(),
            "content": self.get_content(),
            "date": self.get_date(),
        }

    def _get_parts_content(self, message_parts):
        content_types = [p["mimeType"] for p in message_parts if "mimeType" in p.keys()]
        if "text/plain" in content_types:
            return self._get_email_body(
                message_parts=message_parts[content_types.index("text/plain")]
            )
        elif "text/html" in content_types:
            return self._strip_tags(
                html=self._get_email_body(
                    message_parts=message_parts[content_types.index("text/html")]
                )
            )
        elif "multipart/alternative" in content_types:
            return self._get_parts_content(
                message_parts=message_parts[
                    content_types.index("multipart/alternative")
                ]["parts"]
            )
        else:
            return None

    @staticmethod
    def _get_email_body(message_parts):
        return base64.urlsafe_b64decode(
            message_parts["body"]["data"].encode("UTF-8")
        ).decode("UTF-8")

    @staticmethod
    def _strip_tags(html):
        s = MLStripper()
        s.feed(html)
        return s.get_data()
