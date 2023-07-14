from datetime import datetime
import logging
import json

from sqlalchemy import (
    create_engine,
    Column,
    Integer,
    String,
    DateTime,
    Boolean,
    func,
)
from sqlalchemy.orm import sessionmaker
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.engine.url import URL

Base = declarative_base()


def create_session():
    """Создать сессию для работы с базой данных"""
    try:
        with open('src/data/config_mysql.json') as db_config_file:
            config_data = json.load(db_config_file)

        drivername = config_data['drivername']
        username = config_data['username']
        password = config_data['password']
        host = config_data['host']
        port = config_data['port']
        database = config_data['database']

        url_object = URL.create(
            drivername, username, password, host, port, database
        )
        engine = create_engine(url_object, echo=False)

        Session = sessionmaker(bind=engine)
        session = Session()

        return session
    except (FileNotFoundError, KeyError, SQLAlchemyError) as ex:
        logging.error(f'Ошибка при создании сессии базы данных: {ex}')
        return None


def close_session(session):
    """Закрыть сессию базы данных"""
    try:
        session.close()
    except SQLAlchemyError as ex:
        logging.error(f'Ошибка при закрытии сессии базы данных: {ex}')


def check_user_exists(user_id):
    """Проверка существования пользователя в БД по user_id"""
    session = create_session()
    if session is None:
        return
    try:
        user = session.query(User).filter_by(user_id=user_id).first()
        return user is not None
    except SQLAlchemyError as ex:
        session.rollback()
        logging.error(
            f'Возникла ошибка при выполнении операции с базой данных: {ex}'
        )
    finally:
        close_session(session)


def check_user_banned(user_id):
    """Проверка забанен ли пользователь"""
    session = create_session()
    if session is None:
        return
    try:
        user = (
            session.query(User)
            .filter_by(user_id=user_id, banned=False)
            .first()
        )
        return user is None
    except SQLAlchemyError as ex:
        session.rollback()
        logging.error(
            f'Возникла ошибка при выполнении операции с базой данных: {ex}'
        )
    finally:
        close_session(session)


def check_user_admin(user_id):
    """Проверка забанен ли пользователь"""
    session = create_session()
    if session is None:
        return
    try:
        user = (
            session.query(User)
            .filter_by(user_id=user_id, is_admin=True)
            .first()
        )
        return user is not None
    except SQLAlchemyError as ex:
        session.rollback()
        logging.error(
            f'Возникла ошибка при выполнении операции с базой данных: {ex}'
        )
    finally:
        close_session(session)


def insert_new_user(user_name, user_id):
    """Добавить в БД информацию о пользователе, который начал диалог с ботом"""
    session = create_session()
    if session is None:
        return
    try:
        new_user = User(user_name=user_name, user_id=user_id)
        session.add(new_user)
        session.commit()
    except SQLAlchemyError as ex:
        session.rollback()
        logging.error(
            f'Возникла ошибка при выполнении операции с базой данных: {ex}'
        )
    finally:
        close_session(session)


def insert_task_record(id_user, task_link, project_id):
    """Добавить новую запись в таблицу tasks_log о создании задачи пользователем"""
    session = create_session()
    if session is None:
        return
    try:
        # Получение users.id по user_id
        user = session.query(User).filter(User.user_id == id_user).first()
        if user:
            # Вставка записи в tasks_log
            new_task_log = TaskLog(
                user=user.id,
                task_link=task_link,
                datetime_creating=datetime.now(),
                project_id=project_id,
            )
            session.add(new_task_log)
            session.commit()
    except SQLAlchemyError as ex:
        session.rollback()
        logging.error(
            f'Возникла ошибка при выполнении операции с базой данных: {ex}'
        )
    finally:
        close_session(session)


def get_logs(project_id, date):
    session = create_session()
    if session is None:
        return
    try:
        if date is None:
            return (
                session.query(TaskLog, User.user_name, User.user_id)
                .join(User, TaskLog.user == User.id)
                .where(TaskLog.project_id == project_id)
                .order_by(TaskLog.datetime_creating.desc())
                .all()
            )
        else:
            # Объект выбранной даты из календаря
            date_obj = datetime.strptime(date, '%Y-%m-%d')
            return (
                session.query(TaskLog, User.user_name, User.user_id)
                .join(User, TaskLog.user == User.id)
                .where(
                    TaskLog.project_id == project_id,
                    func.DATE(TaskLog.datetime_creating) == date_obj,
                )
                .order_by(TaskLog.datetime_creating.desc())
                .all()
            )
    except SQLAlchemyError as ex:
        logging.error(
            f'Произошла ошибка при выполнении операции с базой данных: {ex}'
        )
    finally:
        close_session(session)


class User(Base):
    __tablename__ = 'users'

    id = Column(Integer, primary_key=True, autoincrement=True)
    user_name = Column(String(50), nullable=False)
    user_id = Column(String(20), nullable=False, unique=True)
    is_admin = Column(Boolean, nullable=False, default=False)
    banned = Column(Boolean, nullable=False, default=False)


class TaskLog(Base):
    __tablename__ = 'tasks_log'

    id = Column(Integer, primary_key=True, autoincrement=True)
    user = Column(Integer, nullable=False)
    task_link = Column(String(100), nullable=False)
    datetime_creating = Column(DateTime, nullable=False)
    project_id = Column(DateTime, nullable=False)
