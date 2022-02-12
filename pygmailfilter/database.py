from sqlalchemy import Column, Integer, String, Boolean
from sqlalchemy.orm import sessionmaker, declarative_base


Base = declarative_base()


class Threads(Base):
    __tablename__ = "threads"
    id = Column(Integer, primary_key=True)
    email_id = Column(String)
    thread_id = Column(String)


class Labels(Base):
    __tablename__ = "labels"
    id = Column(Integer, primary_key=True)
    email_id = Column(String)
    label_id = Column(String)


class EmailTo(Base):
    __tablename__ = "email_to"
    id = Column(Integer, primary_key=True)
    email_id = Column(String)
    email_to = Column(String)


class EmailFrom(Base):
    __tablename__ = "email_from"
    id = Column(Integer, primary_key=True)
    email_id = Column(String)
    email_from = Column(String)


class EmailContent(Base):
    __tablename__ = "email_content"
    id = Column(Integer, primary_key=True)
    email_id = Column(String)
    email_subject = Column(String)
    email_content = Column(String)
    email_deleted = Column(Boolean)


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

    def _build_email_index(self, df, colum_to_index):
        email_id_lst, column_id_lst = [], []
        for eid, email_lst in zip(df["id"], df[colum_to_index]):
            if email_lst is not None:
                email_split_lst = email_lst.split(", ")
                for email_add in [
                    self._get_email_address(email=email) for email in email_split_lst
                ]:
                    email_id_lst.append(eid)
                    column_id_lst.append(email_add)
        return email_id_lst, column_id_lst

    def _commit_thread_table(self, df):
        self._session.add_all(
            [
                Threads(email_id=email_id, thread_id=thread_id)
                for email_id, thread_id in zip(df["id"], df["thread_id"])
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
        email_id_lst, recipe_id_lst = self._build_email_index(
            df=df, colum_to_index="to"
        )
        self._session.add_all(
            [
                EmailTo(email_id=email_id, email_to=email_to)
                for email_id, email_to in zip(email_id_lst, recipe_id_lst)
            ]
        )
        self._session.commit()

    def _commit_email_from_table(self, df):
        email_id_lst, recipe_id_lst = self._build_email_index(
            df=df, colum_to_index="from"
        )
        self._session.add_all(
            [
                EmailFrom(email_id=email_id, email_from=email_from)
                for email_id, email_from in zip(email_id_lst, recipe_id_lst)
            ]
        )
        self._session.commit()

    def _commit_content_table(self, df):
        df_content = df.drop(["thread_id", "label_ids", "to", "from"], axis=1)
        self._session.add_all(
            [
                EmailContent(
                    email_id=email_id,
                    email_subject=email_subject,
                    email_content=email_content,
                    email_deleted=False,
                )
                for email_id, email_subject, email_content in zip(
                    df_content["id"], df_content["subject"], df_content["content"]
                )
            ]
        )
        self._session.commit()

    @staticmethod
    def _create_database_session(engine):
        session = sessionmaker(bind=engine)()
        Base.metadata.create_all(engine)
        return session

    @staticmethod
    def _get_email_address(email):
        email_split = email.split("<")
        if len(email_split) == 1:
            return email.lower()
        else:
            return email_split[1].split(">")[0].lower()
