import pandas


def build_thread_table(df):
    db_id_lst, email_id_lst, thread_id_lst = [], [], []
    for i, [eid, tid] in enumerate(zip(df["id"], df["thread_id"])):
        db_id_lst.append(i)
        email_id_lst.append(eid)
        thread_id_lst.append(tid)
    return pandas.DataFrame(
        {"id": db_id_lst, "email_id": email_id_lst, "thread_id": thread_id_lst}
    )


def build_label_table(df):
    db_id_lst, email_id_lst, label_id_lst = [], [], []
    i = 0
    for eid, lid_lst in zip(df["id"], df["label_ids"]):
        for label in lid_lst:
            db_id_lst.append(i)
            email_id_lst.append(eid)
            label_id_lst.append(label)
            i += 1
    return pandas.DataFrame(
        {"id": db_id_lst, "email_id": email_id_lst, "label_id": label_id_lst}
    )


def get_email_address(email):
    email_split = email.split("<")
    if len(email_split) == 1:
        return email.lower()
    else:
        return email_split[1].split(">")[0].lower()


def build_email_index(df, colum_to_index):
    db_id_lst, email_id_lst, column_id_lst = [], [], []
    i = 0
    for eid, email_lst in zip(df["id"], df[colum_to_index]):
        email_split_lst = email_lst.split(", ")
        for email_add in [get_email_address(email=email) for email in email_split_lst]:
            db_id_lst.append(i)
            email_id_lst.append(eid)
            column_id_lst.append(email_add)
            i += 1
    return db_id_lst, email_id_lst, column_id_lst


def build_email_to_table(df):
    db_id_lst, email_id_lst, recipe_id_lst = build_email_index(
        df=df, colum_to_index="to"
    )
    return pandas.DataFrame(
        {"id": db_id_lst, "email_id": email_id_lst, "email_to": recipe_id_lst}
    )


def build_email_from_table(df):
    db_id_lst, email_id_lst, recipe_id_lst = build_email_index(
        df=df, colum_to_index="from"
    )
    return pandas.DataFrame(
        {"id": db_id_lst, "email_id": email_id_lst, "email_from": recipe_id_lst}
    )


def build_content_table(df):
    return df.drop(["thread_id", "label_ids", "to", "from"], axis=1)
