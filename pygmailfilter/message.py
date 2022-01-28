class Message:
    def __init__(self, message_dict):
        self._message_dict = message_dict

    def get_from(self):
        return [
            entry["value"]
            for entry in self._message_dict['payload']['headers']
            if entry["name"] == "From"
        ][0]

    def get_to(self):
        return [
            entry["value"]
            for entry in self._message_dict['payload']['headers']
            if entry["name"] == "To"
        ][0]

    def get_label_ids(self):
        return self._message_dict["labelIds"]

    def get_subject(self):
        return [
            entry["value"]
            for entry in self._message_dict['payload']['headers']
            if entry["name"] == 'Subject'
        ][0]
