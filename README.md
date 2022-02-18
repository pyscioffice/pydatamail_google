# Manage your emails in Gmail with Python 
[![Python package](https://github.com/pyscioffice/pydatamail_google/actions/workflows/unittest.yml/badge.svg?branch=main)](https://github.com/pyscioffice/pydatamail_google/actions/workflows/unittest.yml)
[![Coverage Status](https://coveralls.io/repos/github/pyscioffice/pydatamail_google/badge.svg?branch=main)](https://coveralls.io/github/pyscioffice/pydatamail_google?branch=main)
[![Code style: black](https://img.shields.io/badge/code%20style-black-000000.svg)](https://github.com/psf/black)

The `pydatamail_google` is a python module to automate the filtering of emails on Gmail using the Gmail API. You can either
write your own python script to combine the different functions or use the `JSON` based input or the command line input, 
all three provide acccess to the same functionality and are explained in more detail below.

# Configuration 
The `pydatamail_google` stores the configuration files in the users home directory `~/.pydatamail`. This folder contains: 

- `config.json` the `JSON` configuration file for `JSON` based input, which is explained in more detial below.  
- `credentials.json` the authentication credentials for the Google API, which at least requires access to Gmail and 
  additional access to Google Drive in case you want to store your attachments on Google drive. 
- `token_files` the token directory is used to store the active token for accessing the APIs, these are created 
  automatically, there should be no need for the user to modify these. 

# Installation 
Install the package from github using `pip`: 
```
pip install git+https://github.com/pyscioffice/pydatamail_google.git
```
Finally setup the `credentials.json` in your Google Apps and store it in `~/.pydatamail/credentials.json`.

# Python interface 
Import the `pydatamail_google` module 
```
from pydatamail_google import Gmail
```

## Initialize pydatamail_google
Create a `gmail` object from the `Gmail()` class
```
gmail = Gmail()
```
For testing purposes you can use the optimal `client_service_file` parameter to specify the location of the 
authentication credentials in case they are not stored in `~/.pydatamail/credentials.json`. 

## List Labels 
List the available labels in your Gmail account:
```
gmail.labels
```
Returns a list of email labels as you defined them in your email client. This is in contrast to the Gmail API which 
typically returns the label IDs rather than the user defined label names. 

## Filter Emails 
Filter a set of emails in a specific label using a predefined list of dictionaries: 
```
gmail.filter_label_by_sender(label, filter_dict_lst)
```
The label can be any email label and the filter_dict_lst is a list of email filters defined as dictionary. A typical 
email filter list might look like this:
```
[{"from": "my_email@provider.com", "label": "my_special_label"},
 {"to": "spam@google.com", "label": "another_email_label"},
 {"subject": "you won", "label": "success_story"}]
```
At the current stage only one of the three fields `from`, `to` or `subject` can be validated per filter and all
filters are applied as "is in" rather than an exact match.

## Search for Emails 
Search emails either by a specific query or optionally limit your search to a list of labels. 
```
gmail.search_email(query_string="", label_lst=[], only_message_ids=False)
```
The `query_string` supports all the functionality the gmail search has to offer, for example you can search for emails 
with attachments using the query `"has:attachment"`. In addition with the option `only_message_ids` the return values
can be reduced to just a list of email ids, otherwise both the email ids and the thread ids are returned. 

## Remove Labels 
As Gmail provides a set of smart labels which are accessible on the web interface but typically hidden in the mobile 
application many people want to remove these labels. Still this functionality is more general and can be applied to
any list of labels, so be warned when using it. 
```
gmail.remove_labels_from_emails(label_lst)
```
To remove the Gmail smart labels just set the `label_lst` to `["CATEGORY_FORUMS", "CATEGORY_UPDATES", 
"CATEGORY_PROMOTIONS", "CATEGORY_SOCIAL"]`.

## Load Tasks from JSON file 
This is the function for the file based interface, which is explained below in a separate section. 
```
gmail.load_json_tasks(config_json=None)
```
By default the json config file is expected to be located in `~/.pydatamail/config.json`. 

## Save attachments for a specific label 
Save all attachments of emails marked with a selected label to a specific folder on Google drive. This requires
Google drive authorisation to be included in the authentication credentials.
```
gmail.save_attachments_of_label(label, path)
```
The label is given by its label name rather than the google internal label ID and the path has to be a relative path
starting at the root of your google drive, for example `backup/emails`. In this path a new subfolder is created with the
name of the label. 

## Download messages to pandas Dataframe
For offline processing it is helpful to download messages in bulk to pandas dataframes:  
```
gmail.download_messages_to_dataframe(message_id_lst)
```
The `message_id_lst` is a list of message ids, this can be obtained from `gmail.search_email()`. 

## Get email content as dictionary 
The content of the email rendered as python dictionary for further postprocessing: 
```
gmail.get_email_dict(message_id)
```
The `message_id` can be derived from a function like `gmail.search_email()`. 

## Update database
Update local database stored in `~/.pydatamail/email.db`:
```
gmail.update_database()
```

# Command Line interface 
The command line interface is currently rather limited, it supports the following options: 

- `pydatamail_google` run the tasks defined in `~/.pydatamail/config.json`.
- `pydatamail_google --file ~/.pydatamail/config.json` run the tasks defined in a user specific task file. 
- `pydatamail_google --labels` list all labels of your Gmail account. 
- `pydatamail_google --database` update local database. 

# File based interface 
Currently the file based interface only supports two functions: 

- `remove_labels_from_emails` to remove specific labels from all emails on your account.
- `filter_label_by_sender` to filter emails using the filter dictionary list 

Both functions are explained in more detail above in the python interface section. Below is an example configuration file
which would be located at `~/.pydatamail/config.json`: 
```
{
    "database": "sqlite:////~/.pydatamail/email.db",
    "remove_labels_from_emails": 
    ["CATEGORY_FORUMS", "CATEGORY_UPDATES", "CATEGORY_PROMOTIONS", "CATEGORY_SOCIAL"], 
    "filter_label_by_sender": {
        "label": "my_other_email_provider", 
        "filter_dict_lst": [
            {"from": "my_email@provider.com", "label": "my_special_label"},
            {"to": "spam@google.com", "label": "another_email_label"},
            {"subject": "you won", "label": "success_story"}
        ]
    }
}
```
