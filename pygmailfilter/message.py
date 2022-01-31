class Message:
    def __init__(self, message_dict):
        self._message_dict = message_dict

    def get_from(self):
        lst = [
            entry["value"]
            for entry in self._message_dict["payload"]["headers"]
            if entry["name"] == "From"
        ]
        if len(lst) > 0:
            return lst[0]
        else:
            return None

    def get_to(self):
        lst = [
            entry["value"]
            for entry in self._message_dict["payload"]["headers"]
            if entry["name"] == "To"
        ]
        if len(lst) > 0:
            return lst[0]
        else:
            return None

    def get_label_ids(self):
        return self._message_dict["labelIds"]

    def get_subject(self):
        lst = [
            entry["value"]
            for entry in self._message_dict["payload"]["headers"]
            if entry["name"] == "Subject"
        ]
        if len(lst) > 0:
            return lst[0]
        else:
            return None
