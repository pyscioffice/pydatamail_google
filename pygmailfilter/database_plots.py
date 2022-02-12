import pandas
import numpy as np
import matplotlib.pyplot as plt


def get_from_pie_plot(df, minimum_emails=25):
    df["from"].value_counts()
    dict_values = np.array(list(df["from"].value_counts().to_dict().values()))
    dict_keys = np.array(list(df["from"].value_counts().to_dict().keys()))
    ind = dict_values > minimum_emails
    dict_values_red = dict_values[ind].tolist()
    dict_keys_red = dict_keys[ind].tolist()
    dict_values_red.append(sum(dict_values[~ind]))
    dict_keys_red.append("other")

    fig1, ax1 = plt.subplots()
    ax1.pie(dict_values_red, labels=dict_keys_red)
    ax1.axis("equal")
    plt.show()


def get_labels_pie_plot(gmail, df):
    label_lst = []
    for llst in df.labels.values:
        for ll in llst:
            label_lst.append(ll)

    label_lst = list(set(label_lst))
    label_lst = [label for label in label_lst if "Label_" in label]
    label_count_lst = [
        sum([True if label_select in label else False for label in df.labels])
        for label_select in label_lst
    ]
    convert_dict = {
        v: k
        for v, k in zip(
            list(gmail._label_dict.values()), list(gmail._label_dict.keys())
        )
    }
    label_convert_lst = [convert_dict[label] for label in label_lst]
    ind = np.argsort(label_count_lst)

    fig1, ax1 = plt.subplots()
    ax1.pie(
        np.array(label_count_lst)[ind][::-1],
        labels=np.array(label_convert_lst)[ind][::-1],
    )
    ax1.axis("equal")
    plt.show()


def get_number_of_email_plot(df, steps=8):
    start_month = [d.year * 12 + d.month for d in pandas.to_datetime(df.date)]

    plt.hist(start_month)
    plt.xticks(
        np.linspace(np.min(start_month), np.max(start_month), steps),
        [
            str(int(month // 12)) + "-" + str(int(month % 12))
            for month in np.linspace(np.min(start_month), np.max(start_month), steps)
        ],
    )
    plt.xlabel("Date")
    plt.ylabel("Number of Emails")
