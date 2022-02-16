import argparse
from pydatamail_google.local import Gmail


def command_line_parser():
    """
    Main function primarly used for the command line interface
    """
    parser = argparse.ArgumentParser(prog="pydatamail_google")
    parser.add_argument(
        "-f",
        "--file",
        action="store_true",
        help="Additional configuration file to store tasks.",
    )
    parser.add_argument(
        "-l",
        "--labels",
        action="store_true",
        help="List available labels on Gmail.",
    )
    parser.add_argument(
        "-d",
        "--database",
        action="store_true",
        help="Update local database.",
    )
    parser.add_argument(
        "-s",
        "--search",
        help="Search emails on Gmail.",
    )
    parser.add_argument(
        "-c",
        "--config",
        help="Configuration Folder e.g. ~/.pydatamail_google",
    )
    args = parser.parse_args()
    if args.config:
        gmail = Gmail(config_folder=args.config)
    else:
        gmail = Gmail()
    if args.file:
        gmail.load_json_tasks(config_json=args.file)
    elif args.labels:
        print(gmail.labels)
    elif args.search:
        print(gmail.search_email(query_string=args.search, only_message_ids=True))
    elif args.database:
        gmail.update_database()
    else:
        gmail.load_json_tasks()


if __name__ == "__main__":
    command_line_parser()
