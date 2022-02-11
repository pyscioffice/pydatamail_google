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

    def commit_thread_table(self, df):
        self._session.add_all(
            [
                Threads(email_id=email_id, thread_id=thread_id)
                for email_id, thread_id in zip(df["id"], df["thread_id"])
            ]
        )
        self._session.commit()

    def commit_label_table(self, df):
        label_lst = []
        for email_id, lid_lst in zip(df["id"], df["label_ids"]):
            for label_id in lid_lst:
                label_lst.append(Labels(email_id=email_id, label_id=label_id))
        self._session.add_all(label_lst)
        self._session.commit()

    def commit_email_to_table(self, df):
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

    def commit_email_from_table(self, df):
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

    def commit_content_table(self, df):
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

    def _build_email_index(self, df, colum_to_index):
        email_id_lst, column_id_lst = [], []
        for eid, email_lst in zip(df["id"], df[colum_to_index]):
            email_split_lst = email_lst.split(", ")
            for email_add in [
                self._get_email_address(email=email) for email in email_split_lst
            ]:
                email_id_lst.append(eid)
                column_id_lst.append(email_add)
        return email_id_lst, column_id_lst

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
