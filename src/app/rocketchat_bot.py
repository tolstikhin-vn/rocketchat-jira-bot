import logging
import requests
import time
from typing import Any, List, Dict, Optional

import database
from jira_client import Issue, JiraClient

CREATE_TASK = 'Создать задачу'
START_OVER = 'Заново'
VIEW_LOGS = 'Логи'
BACK = 'Назад'
ONLINE_STATUS = 'online'
WELCOME_MESSAGE = 'Привет, я помогу тебе создать задачу в Jira. Нажимай на кнопку "Создать задачу".'
ENTER_TASK_NAME = 'Введите название будущей задачи:'
PROJECT_NOT_FOUND = 'Проект с таким названием не найден.'
ENTER_TASK_DESC = 'Введите описание будущей задачи:'
USER_BANNED = 'Вы заблокированы администратором!'

# Экземпляр класса JiraClient
jira_client: JiraClient = JiraClient()

# Экземпляр класса Issue
issue: Issue = Issue()


def catch_exceptions(func):
    """Обработка исключений"""

    def wrapper(*args, **kwargs):
        try:
            return func(*args, **kwargs)
        except requests.exceptions.RequestException as ex:
            logging.exception(f'Возникло исключение: {ex}')

    return wrapper


class RocketChatBot:
    """Класс для работы с Rocket.Chat"""

    # Текущая стадия создания задачи
    creation_stage: int = 0

    def __init__(self, base_url, username, password, bot_id):
        self.base_url: str = base_url
        self.username: str = username
        self.password: str = password
        self.bot_id: str = bot_id
        self.auth_token: Optional[str] = None

    @catch_exceptions
    def get_auth_token(self) -> None:
        """Получить токен авторизации по логину и паролю бота-пользователя для работы от его лица"""
        login_url: str = f'{self.base_url}login'
        data: Dict[str, str] = {
            'user': self.username,
            'password': self.password,
        }
        response = requests.post(login_url, json=data)
        response.raise_for_status()
        self.auth_token = response.json()['data']['authToken']

    @catch_exceptions
    def set_status(self, status_name) -> None:
        """Задать статус бота"""
        set_status_url = f'{self.base_url}users.setStatus'
        headers: Dict[str, str] = {
            'X-Auth-Token': self.auth_token,
            'X-User-Id': self.bot_id,
        }
        status_data: Dict[str, str] = {'status': status_name}
        requests.post(set_status_url, headers=headers, json=status_data)

    @catch_exceptions
    def send_message(self, data: dict) -> None:
        """Отправить сообщение в чат"""
        send_msg_url = f'{self.base_url}chat.postMessage'
        headers: Dict[str, str] = {
            'X-Auth-Token': self.auth_token,
            'X-User-Id': self.bot_id,
        }

        requests.post(send_msg_url, headers=headers, json=data)

    @catch_exceptions
    def get_direct_messages(self) -> List[Dict[str, Any]]:
        """Получить список сообщений из чата"""
        dm_url: str = f'{self.base_url}im.list'
        headers: Dict[str, str] = {
            'X-Auth-Token': self.auth_token,
            'X-User-Id': self.bot_id,
        }
        response = requests.get(dm_url, headers=headers)
        response.raise_for_status()
        dms: List[Dict[str, Any]] = response.json()['ims']
        return dms

    def get_action_structure(
        self, text: str, url: Optional[str], message: str
    ) -> Dict[str, Any]:
        """Получить структуру с кнопкой для actions в сообщении Rocket.Chat"""
        action_structure: Dict[str, Any] = {
            'type': 'button',
            'text': text,
            'msg_in_chat_window': True,
            'button_alignment': 'vertical',
            'button_color': '#FF0000',
            'button_text_color': '#FFFFFF',
            'msg': message,
        }

        # Если передан url, добавляем его в свойства кнопки (для админа)
        if url is not None:
            action_structure['url'] = url

        return action_structure

    def get_data_for_stage_0(
        self, room_id: int, message: str, is_admin: bool
    ) -> Dict[str, Any]:
        """Получить представление для вывода сообщения с кнопкой создания задачи"""

        actions: List[Dict[str, Any]] = []
        actions.append(
            self.get_action_structure(CREATE_TASK, None, CREATE_TASK)
        )
        actions.append(self.get_action_structure(BACK, None, BACK))
        actions.append(self.get_action_structure(START_OVER, None, START_OVER))

        if is_admin:
            actions.append(
                self.get_action_structure(
                    VIEW_LOGS, 'http://127.0.0.1:8000/logs', VIEW_LOGS
                )
            )
        return {
            'channel': room_id,
            'text': message,
            'attachments': [
                {
                    'color': '#FFFFFF',
                    'actions': actions,
                },
            ],
        }

    def get_data_for_stage_1(
        self, room_id: int, projects: List[Any]
    ) -> Dict[str, Any]:
        """Получить представление для вывода списка проектов в чат"""
        actions: List[Dict[str, Any]] = []

        # Сгенерировать кнопки по количеству проектов
        for project in projects:
            actions.append(
                self.get_action_structure(project.name, None, project.name)
            )

        return {
            'channel': room_id,
            'text': 'Выберите проект:',
            'attachments': [
                {
                    'color': '#FFFFFF',
                    'actions': actions,
                }
            ],
        }

    def get_base_data(self, room_id: int, message: str) -> Dict[str, str]:
        """Получить базовое JSON-представление из id комнаты и сообщения"""
        return {'roomId': room_id, 'text': message}

    @catch_exceptions
    def go_to_next_stage(
        self, creation_stage, room_id, message_text, user_id, user_name
    ) -> None:
        """Логика переходов между этапами создания задачи"""
        if creation_stage == 0:
            self.send_message(
                self.get_data_for_stage_0(
                    room_id,
                    WELCOME_MESSAGE,
                    database.check_user_admin(user_id),
                ),
            )

        # Стадия 1 - ожидание ввода названия проекта от пользователя
        elif creation_stage == 1:
            projects: List[Any] = jira_client.get_projects()

            # Бот отправляет в чат список проектов в виде кнопок
            self.send_message(
                self.get_data_for_stage_1(
                    room_id,
                    projects,
                )
            )

            # Перейти на следующую стадию
            self.creation_stage = 2

        # Стадия 2 - ожидание ввода названия задачи от пользователя
        elif creation_stage == 2:
            projects: List[Any] = jira_client.get_projects()

            if jira_client.get_project_name() is not None:
                self.send_message(self.get_base_data(room_id, ENTER_TASK_NAME))
                self.creation_stage = 3

            # Если проект с таким названием существует
            elif any(message_text == project.name for project in projects):
                self.send_message(self.get_base_data(room_id, ENTER_TASK_NAME))
                jira_client.set_project_name(message_text)
                self.creation_stage = 3
            else:
                self.send_message(
                    self.get_base_data(room_id, PROJECT_NOT_FOUND)
                )

        elif creation_stage == 3:
            issue.set_issue_summary(message_text)
            self.send_message(self.get_base_data(room_id, ENTER_TASK_DESC))
            self.creation_stage = 4

        # Стадия 4 - создание задачи исходя из полученных данных от пользователя
        elif creation_stage == 4:
            issue.set_issue_description(message_text)
            projects: List[Any] = jira_client.get_projects()

            # Ищем ключ проекта по его названию
            project_key: Optional[str] = None
            project_id: Optional[int] = None
            for project in projects:
                if jira_client.get_project_name() == project.name:
                    project_key = project.key
                    project_id = project.id
                    break

            # Получаем название задачи
            issue_summary: str = (
                f'(от {user_name}) {issue.get_issue_summary()}'
            )

            # Создаем новую задачу
            if jira_client.create_new_issue(
                project_key,
                issue_summary,
                issue.get_issue_description(),
            ):
                # Получаем ссылку на задачу
                task_link: str = jira_client.get_issue_link(
                    project_key, issue_summary
                )

                self.send_message(
                    self.get_base_data(
                        room_id,
                        f'[Задача]({task_link}) успешно создана!',
                    )
                )
            else:
                self.send_message(
                    self.get_base_data(
                        room_id,
                        'Ошибка создания задачи. Попробуйте позднее.',
                    )
                )

            # Добавляем запись о создании задачи
            database.insert_task_record(user_id, task_link, project_id)

            # Все заново
            self.creation_stage = 0

    @catch_exceptions
    def process_messages(self) -> None:
        """Обработать новое сообщение"""
        # Список сообщений из чата
        dms: List[Dict[str, Any]] = self.get_direct_messages()
        if dms is not None:
            for dm in dms:
                user_id: str = dm['lastMessage']['u']['_id']
                room_id: str = dm['_id']
                if 'lastMessage' in dm and user_id != self.bot_id:
                    if database.check_user_exists(user_id):
                        if database.check_user_banned(user_id):
                            self.send_message(
                                self.get_base_data(room_id, USER_BANNED)
                            )
                            break
                    else:
                        # Добавляем пользователя чата в БД, если он еще не добавлен
                        database.insert_new_user(
                            dm['lastMessage']['u']['username'],
                            user_id,
                        )
                    last_msg: Dict[str, Any] = dm['lastMessage']
                    message_text: str = last_msg['msg']

                    if message_text == BACK:
                        if self.creation_stage > 0:
                            self.dec_creation_stage()
                    elif message_text == CREATE_TASK:
                        self.creation_stage = 1
                    elif message_text == START_OVER:
                        self.creation_stage = 0

                    user_name: str = dm['lastMessage']['u']['username']

                    # Перейти на новую стадию
                    self.go_to_next_stage(
                        self.creation_stage,
                        room_id,
                        message_text,
                        user_id,
                        user_name,
                    )

    def dec_creation_stage(self) -> None:
        """Уменьшить индекс текущей стадии создания при нажатии кнопки Назад"""
        if self.creation_stage == 1:
            self.creation_stage = 0
        elif self.creation_stage == 2:
            self.creation_stage = 0
        elif self.creation_stage == 3:
            self.creation_stage = 1
        elif self.creation_stage == 4:
            self.creation_stage = 2

    def run(self) -> None:
        """Основная функция, отвечающая за запуск бота"""
        self.get_auth_token()
        self.set_status(ONLINE_STATUS)
        while True:
            try:
                self.process_messages()
                time.sleep(0.1)
            except TimeoutError:
                time.sleep(10)
