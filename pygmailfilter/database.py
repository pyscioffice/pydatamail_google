import pandas
from tqdm import tqdm
from sqlalchemy import Column, Integer, String, Boolean, DateTime, ForeignKey
from sqlalchemy.orm import sessionmaker, declarative_base


Base = declarative_base()


class EmailContent(Base):
    __tablename__ = "email_content"
    id = Column(Integer, primary_key=True)
    email_id = Column(String)
    email_subject = Column(String)
    email_content = Column(String)
    email_deleted = Column(Boolean)
    email_date = Column(DateTime)


class Threads(Base):
    __tablename__ = "threads"
    id = Column(Integer, primary_key=True)
    email_id = Column(String, ForeignKey("email_content.email_id"))
    thread_id = Column(String)


class Labels(Base):
    __tablename__ = "labels"
    id = Column(Integer, primary_key=True)
    email_id = Column(String, ForeignKey("email_content.email_id"))
    label_id = Column(String)


class EmailTo(Base):
    __tablename__ = "email_to"
    id = Column(Integer, primary_key=True)
    email_id = Column(String, ForeignKey("email_content.email_id"))
    email_to = Column(String)


class EmailFrom(Base):
    __tablename__ = "email_from"
    id = Column(Integer, primary_key=True)
    email_id = Column(String, ForeignKey("email_content.email_id"))
    email_from = Column(String)


class DatabaseInterface:
    def __init__(self, engine):
        self._session = self._create_database_session(engine=engine)

    @property
    def session(self):
        return self._session

    def store_dataframe(self, df):
        self._commit_content_table(df=df)
        self._commit_email_from_table(df=df)
        self._commit_email_to_table(df=df)
        self._commit_label_table(df=df)
        self._commit_thread_table(df=df)

    def list_email_ids(self):
        return [
            instance.email_id
            for instance in self._session.query(EmailContent).order_by(EmailContent.id)
        ]

    def mark_emails_as_deleted(self, message_id_lst):
        for instance in (
            self._session.query(EmailContent)
            .filter(EmailContent.email_id.in_(message_id_lst))
            .all()
        ):
            instance.email_deleted = True
        self._session.commit()

    def get_labels_to_update(self, message_id_lst):
        email_in_db_id = self.list_email_ids()
        new_messages_lst = [m for m in message_id_lst if m not in email_in_db_id]
        deleted_messages_lst = [m for m in email_in_db_id if m not in message_id_lst]
        message_label_updates_lst = [m for m in message_id_lst if m in email_in_db_id]
        return new_messages_lst, message_label_updates_lst, deleted_messages_lst

    def update_labels(self, message_id_lst, message_meta_lst):
        for message_id, message_labels in zip(message_id_lst, message_meta_lst):
            message_label_stored = [
                m
                for m, in self._session.query(Labels.label_id)
                .filter(Labels.email_id == message_id)
                .all()
            ]
            if message_label_stored == message_labels:
                continue
            else:
                message_label_stored_set = set(message_label_stored)
                message_labels_set = set(message_labels)
                labels_to_add = list(
                    message_labels_set.difference(message_label_stored_set)
                )
                labels_to_remove = list(
                    message_label_stored_set.difference(message_labels_set)
                )
                if len(labels_to_add) > 0:
                    self._session.add_all(
                        [
                            Labels(email_id=message_id, label_id=label_id)
                            for label_id in labels_to_add
                        ]
                    )
                if len(labels_to_remove) > 0:
                    for label_id in labels_to_remove:
                        self._session.query(Labels).filter(
                            Labels.email_id == message_id
                        ).filter(Labels.label_id == label_id).delete()
                self._session.commit()

    def get_all_emails(self, include_deleted=False):
        if include_deleted:
            email_collect_lst = [
                [
                    email.email_id,
                    email.email_subject,
                    email.email_content,
                    email.email_date,
                ]
                for email in self._session.query(EmailContent).all()
            ]
        else:
            email_collect_lst = [
                [
                    email.email_id,
                    email.email_subject,
                    email.email_content,
                    email.email_date,
                ]
                for email in self._session.query(EmailContent)
                .filter(EmailContent.email_deleted == False)
                .all()
            ]
        return self._create_dataframe(email_collect_lst=email_collect_lst)

    def get_emails_by_label(self, label_id):
        return self._get_email_collection(
            email_id_lst=[
                email_id
                for email_id, in self._session.query(Labels.email_id)
                .filter(Labels.label_id == label_id)
                .all()
            ]
        )

    def get_emails_by_from(self, email_from):
        return self._get_email_collection(
            email_id_lst=[
                email_id
                for email_id, in self._session.query(EmailFrom.email_id)
                .filter(EmailFrom.email_from == email_from)
                .all()
            ]
        )

    def get_emails_by_to(self, email_to):
        return self._get_email_collection(
            email_id_lst=[
                email_id
                for email_id, in self._session.query(EmailTo.email_id)
                .filter(EmailTo.email_to == email_to)
                .all()
            ]
        )

    def get_emails_by_thread(self, thread_id):
        return self._get_email_collection(
            email_id_lst=[
                email_id
                for email_id, in self._session.query(Threads.email_id)
                .filter(Threads.thread_id == thread_id)
                .all()
            ]
        )

    def _get_email_collection(self, email_id_lst):
        email_collect_lst = [
            [email.email_id, email.email_subject, email.email_content, email.email_date]
            for email in self._session.query(EmailContent)
            .filter(EmailContent.email_id.in_(email_id_lst))
            .all()
        ]
        return self._create_dataframe(email_collect_lst=email_collect_lst)

    def _commit_thread_table(self, df):
        self._session.add_all(
            [
                Threads(email_id=email_id, thread_id=thread_id)
                for email_id, thread_id in zip(df["id"], df["thread_id"])
            ]
        )
        self._session.commit()

    def _commit_email_from_table(self, df):
        self._session.add_all(
            [
                EmailFrom(email_id=email_id, email_from=email_from)
                for email_id, email_from in zip(df["id"], df["from"])
            ]
        )
        self._session.commit()

    def _commit_label_table(self, df):
        label_lst = []
        for email_id, lid_lst in zip(df["id"], df["label_ids"]):
            for label_id in lid_lst:
                label_lst.append(Labels(email_id=email_id, label_id=label_id))
        self._session.add_all(label_lst)
        self._session.commit()

    def _commit_email_to_table(self, df):
        email_to_lst = []
        for email_id, email_lst in zip(df["id"], df["to"]):
            for email_to in email_lst:
                email_to_lst.append(EmailTo(email_id=email_id, email_to=email_to))
        self._session.add_all(email_to_lst)
        self._session.commit()

    def _commit_content_table(self, df):
        self._session.add_all(
            [
                EmailContent(
                    email_id=email_id,
                    email_subject=email_subject,
                    email_content=email_content,
                    email_deleted=False,
                    email_date=email_date,
                )
                for email_id, email_subject, email_content, email_date in zip(
                    df["id"], df["subject"], df["content"], df["date"]
                )
            ]
        )
        self._session.commit()

    def _create_dataframe(self, email_collect_lst):
        (
            email_id_lst,
            email_subject_lst,
            email_content_lst,
            email_from_lst,
            email_to_lst,
            email_threads_lst,
            email_labels_lst,
            email_date_lst,
        ) = ([], [], [], [], [], [], [], [])
        for email_id, email_subject, email_content, email_date in tqdm(
            email_collect_lst
        ):
            email_from = [
                email_from.email_from
                for email_from in self._session.query(EmailFrom)
                .filter(EmailFrom.email_id == email_id)
                .all()
            ]
            email_to = [
                email_to.email_to
                for email_to in self._session.query(EmailTo)
                .filter(EmailTo.email_id == email_id)
                .all()
            ]
            label_lst = [
                labels.label_id
                for labels in self._session.query(Labels)
                .filter(Labels.email_id == email_id)
                .all()
            ]
            thread_lst = [
                threads.thread_id
                for threads in self._session.query(Threads)
                .filter(Threads.email_id == email_id)
                .all()
            ]
            if len(email_from) > 0:
                email_from_lst.append(email_from[0])
            else:
                email_from_lst.append(None)
            email_to_lst.append(email_to)
            email_labels_lst.append(label_lst)
            email_threads_lst.append(thread_lst[0])
            email_id_lst.append(email_id)
            email_subject_lst.append(email_subject)
            email_content_lst.append(email_content)
            email_date_lst.append(email_date)
        return pandas.DataFrame(
            {
                "id": email_id_lst,
                "from": email_from_lst,
                "to": email_to_lst,
                "date": email_date_lst,
                "threads": email_threads_lst,
                "labels": email_labels_lst,
                "subject": email_subject_lst,
                "content": email_content_lst,
            }
        )

    @staticmethod
    def _create_database_session(engine):
        session = sessionmaker(bind=engine)()
        Base.metadata.create_all(engine)
        return session
