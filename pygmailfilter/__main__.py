from pygmailfilter.gmail import Gmail


def load_json_tasks():
    Gmail().load_json_tasks()


if __name__ == "__main__":
    load_json_tasks()
