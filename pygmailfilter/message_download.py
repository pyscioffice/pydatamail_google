import base64
from io import StringIO
from html.parser import HTMLParser


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


def strip_tags(html):
    s = MLStripper()
    s.feed(html)
    return s.get_data()


def get_email_content(message):
    if "parts" not in message["payload"].keys():
        return None
    content_types = [p["mimeType"] for p in message["payload"]["parts"]]
    if "text/plain" in content_types:
        return _get_email_body(message=message, ind=content_types.index("text/plain"))
    elif "text/html" in content_types:
        return strip_tags(
            html=_get_email_body(message=message, ind=content_types.index("text/html"))
        )
    else:
        return None


def _get_email_body(message, ind):
    return base64.urlsafe_b64decode(
        message["payload"]["parts"][ind]["body"]["data"].encode("UTF-8")
    ).decode("UTF-8")
