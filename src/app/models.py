import logging
from sqlalchemy import create_engine, Column, Integer, String, DateTime
from sqlalchemy.orm import relationship, sessionmaker
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.engine.url import URL

url_object = URL.create(
    drivername='mysql+pymysql',
    username='mysqluser',
    password='mysqlpassword',
    host='192.168.56.50',
    port='3306',
    database='rocketchat_db',
)

engine = create_engine(url_object, echo=False)

Session = sessionmaker(bind=engine)
session = Session()


Base = declarative_base()


def insert_new_user(user_name, user_id):
    """Добавить в БД информациюю о пользователе, который начал диалог с ботом"""
    try:
        user = session.query(User).filter_by(user_id=user_id).first()

        # Если пользователь не существует, создаем новую запись в таблице users
        if not user:
            new_user = User(user_name=user_name, user_id=user_id)
            session.add(new_user)
            session.commit()
    except SQLAlchemyError as ex:
        session.rollback()
        logging.error(
            f'Возникла ошибка при выполнении операции с базой данных: {ex}'
        )
    finally:
        session.close()


# def insert_task_record(id_user, task_link):
#     """Добавить новую запись в таблицу tasks_log о создании задачи пользователем"""
#     try:
#         # Получение users.id по user_id
#         user = session.query(User).filter(User.user_id == id_user).first()
#         if user:
#             # Вставка записи в tasks_log
#             task_link = 'your_task_link'
#             new_task_log = TaskLog(id_user=user.id, task_link=task_link)
#             session.add(new_task_log)
#             session.commit()
#             print('Запись успешно добавлена в tasks_log')
#         else:
#             print('Пользователь с указанным user_id не найден')
#     except SQLAlchemyError as ex:
#         session.rollback()
#         logging.error(
#             f'Возникла ошибка при выполнении операции с базой данных: {ex}'
#         )
#     finally:
#         session.close()


class User(Base):
    __tablename__ = 'users'

    id = Column(Integer, primary_key=True, autoincrement=True)
    user_name = Column(String(50), nullable=False)
    user_id = Column(String(20), nullable=False, unique=True)


class TaskLog(Base):
    __tablename__ = 'tasks_log'

    id = Column(Integer, primary_key=True, autoincrement=True)
    id_user = Column(Integer, nullable=False)
    task_link = Column(String(100), nullable=False)
    user = relationship('User', backref='tasks_log')
