from datetime import datetime
from typing import Any, List, Tuple, Dict
import logging
import json

from sqlalchemy import (
    create_engine,
    Column,
    Integer,
    String,
    DateTime,
    Boolean,
)
from sqlalchemy.orm import sessionmaker
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.engine.url import URL

Base: Any = declarative_base()


def create_session() -> sessionmaker:
    """Создать сессию для работы с базой данных"""
    try:
        with open('src/data/config_mysql.json') as db_config_file:
            config_data: Dict[str, Any] = json.load(db_config_file)

        drivername: str = config_data['drivername']
        username: str = config_data['username']
        password: str = config_data['password']
        host: str = config_data['host']
        port: int = config_data['port']
        database: str = config_data['database']

        url_object: URL = URL.create(
            drivername, username, password, host, port, database
        )
        engine = create_engine(url_object, echo=False)

        Session: sessionmaker = sessionmaker(bind=engine)
        session: sessionmaker = Session()

        return session
    except (FileNotFoundError, KeyError, SQLAlchemyError) as ex:
        logging.error(f'Ошибка при создании сессии базы данных: {ex}')
        return None


def close_session(session) -> None:
    """Закрыть сессию базы данных"""
    try:
        session.close()
    except SQLAlchemyError as ex:
        logging.error(f'Ошибка при закрытии сессии базы данных: {ex}')


def check_user_exists(user_id) -> bool:
    """Проверка существования пользователя в БД по user_id"""
    session = create_session()
    if session is None:
        return
    try:
        user = session.query(User).filter_by(user_id=user_id).first()
        return user is not None
    except SQLAlchemyError as ex:
        logging.error(
            f'Возникла ошибка при выполнении операции с базой данных: {ex}'
        )
    finally:
        close_session(session)


def check_user_banned(user_id) -> bool:
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
        logging.error(
            f'Возникла ошибка при выполнении операции с базой данных: {ex}'
        )
    finally:
        close_session(session)


def check_user_admin(user_id) -> bool:
    """Проверка Пользователя на роль админа"""
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
        logging.error(
            f'Возникла ошибка при выполнении операции с базой данных: {ex}'
        )
    finally:
        close_session(session)


def insert_new_user(user_name, user_id) -> None:
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


def insert_task_record(id_user, task_link, project_id) -> None:
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


def get_logs_from_db(project_id, startDate, endDate) -> List[Tuple]:
    """Получить информацию об истории создания задач для формирования таблицы"""
    session = create_session()
    if session is None:
        return
    try:
        # Преобразование startDate и endDate в объекты типа datetime
        start_datetime: datetime = datetime.strptime(
            startDate, '%Y-%m-%d'
        ).replace(hour=0, minute=0, second=0)
        end_datetime: datetime = datetime.strptime(
            endDate, '%Y-%m-%d'
        ).replace(hour=23, minute=59, second=59)

        return (
            session.query(TaskLog, User.user_name, User.user_id)
            .join(User, TaskLog.user == User.id)
            .where(
                TaskLog.project_id == project_id,
                TaskLog.datetime_creating.between(
                    start_datetime, end_datetime
                ),
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
    """Класс для представления таблицы users"""

    __tablename__ = 'users'

    id: int = Column(Integer, primary_key=True, autoincrement=True)
    user_name: str = Column(String(50), nullable=False)
    user_id: str = Column(String(20), nullable=False, unique=True)
    is_admin: bool = Column(Boolean, nullable=False, default=False)
    banned: bool = Column(Boolean, nullable=False, default=False)


class TaskLog(Base):
    """Класс для представления таблицы tasks_log"""

    __tablename__ = 'tasks_log'

    id: int = Column(Integer, primary_key=True, autoincrement=True)
    user: int = Column(Integer, nullable=False)
    task_link: str = Column(String(100), nullable=False)
    datetime_creating: datetime = Column(DateTime, nullable=False)
    project_id: str = Column(DateTime, nullable=False)
