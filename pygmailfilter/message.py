def get_header_field_from_message(message, field):
    lst = [
        entry["value"]
        for entry in message["payload"]["headers"]
        if entry["name"] == field
    ]
    if len(lst) > 0:
        return lst[0]
    else:
        return None


class Message:
    def __init__(self, message_dict):
        self._message_dict = message_dict

    def get_from(self):
        return get_header_field_from_message(message=self._message_dict, field="From")

    def get_to(self):
        return get_header_field_from_message(message=self._message_dict, field="To")

    def get_label_ids(self):
        return self._message_dict["labelIds"]

    def get_subject(self):
        return get_header_field_from_message(
            message=self._message_dict, field="Subject"
        )
