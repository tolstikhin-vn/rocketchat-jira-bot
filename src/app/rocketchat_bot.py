import logging
import requests
import time
import models
from jira_client import Issue, JiraClient


def catch_exceptions(func):
    """Обработка исключений"""

    def wrapper(*args, **kwargs):
        try:
            return func(*args, **kwargs)
        except requests.exceptions.RequestException as ex:
            logging.exception(f'Возникло исключение: {ex}')

    return wrapper


# Будущий экземпляр класса JiraClient
jira_client = None

# Экземпляр класса Issue
issue = Issue()


class RocketChatBot:

    # Текущая стадия создания задачи
    creation_stage = 0

    def __init__(self, base_url, username, password, bot_id):
        self.base_url = base_url
        self.username = username
        self.password = password
        self.bot_id = bot_id
        self.auth_token = None

    @catch_exceptions
    def get_auth_token(self):
        """Получить токен авторизации по логину и паролю бота-пользователя для работы от его лица"""
        login_url = f'{self.base_url}login'
        data = {'user': self.username, 'password': self.password}
        response = requests.post(login_url, json=data)
        response.raise_for_status()
        self.auth_token = response.json()['data']['authToken']

    @catch_exceptions
    def set_status(self, status_name):
        """Задать статус бота"""
        set_status_url = f'{self.base_url}users.setStatus'
        headers = {
            'X-Auth-Token': self.auth_token,
            'X-User-Id': self.bot_id,
        }
        status_data = {'status': status_name}
        requests.post(set_status_url, headers=headers, json=status_data)

    @catch_exceptions
    def send_message(self, data):
        """Отправить сообщения в чат"""
        send_msg_url = f'{self.base_url}chat.postMessage'
        headers = {
            'X-Auth-Token': self.auth_token,
            'X-User-Id': self.bot_id,
        }

        requests.post(send_msg_url, headers=headers, json=data)

    @catch_exceptions
    def get_direct_messages(self):
        """Получить список сообщений"""
        dm_url = f'{self.base_url}im.list'
        headers = {
            'X-Auth-Token': self.auth_token,
            'X-User-Id': self.bot_id,
        }
        response = requests.get(dm_url, headers=headers)
        response.raise_for_status()
        dms = response.json()['ims']
        return dms

    def get_data_for_stage_0(self, room_id, message):
        """Получение предствления для вывода сообщения с кнопкой создания задачи"""
        return {
            'channel': room_id,
            'text': message,
            'attachments': [
                {
                    'color': '#FFFFFF',
                    'actions': [
                        {
                            'type': 'button',
                            'text': 'Создать задачу',
                            'msg_in_chat_window': True,
                            'button_alignment': 'vertical',
                            'button_color': '#FF0000',
                            'button_text_color': '#FFFFFF',
                            'msg': 'Создать задачу',
                        }
                    ],
                },
                {
                    'actions': [
                        {
                            'type': 'button',
                            'text': 'Начать заново',
                            'msg_in_chat_window': True,
                            'button_alignment': 'vertical',
                            'button_color': '#FF0000',
                            'button_text_color': '#FFFFFF',
                            'msg': 'Начать заново',
                        }
                    ]
                },
            ],
        }

    def get_data_for_stage_1(self, room_id, projects):
        """Получение представление для вывода списка проектов в чат"""
        actions = []

        # Сгенерировать кнопки по количеству проектов
        for project in projects:
            action = {
                'type': 'button',
                'text': project.name,
                'msg_in_chat_window': True,
                'button_alignment': 'vertical',
                'button_color': '#FF0000',
                'button_text_color': '#FFFFFF',
                'msg': project.name,
            }
            actions.append(action)

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

    def get_data_for_stage_1(self, room_id, projects):
        """Получение представление для вывода списка проектов в чат"""
        actions = []

        # Сгенерировать кнопки по количеству проектов
        for project in projects:
            action = {
                'type': 'button',
                'text': project.name,
                'msg_in_chat_window': True,
                'button_alignment': 'vertical',
                'button_color': '#FF0000',
                'button_text_color': '#FFFFFF',
                'msg': project.name,
            }
            actions.append(action)

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

    def get_base_data(self, room_id, message):
        """Получить базовое JSON-представление из id комнаты и сообщения"""
        return {'roomId': room_id, 'text': message}

    @catch_exceptions
    def go_to_next_stage(self, creation_stage, room_id, message_text, user_id):
        """Логика переходов между этапы создания задачи"""
        global jira_client
        if creation_stage == 0:
            self.send_message(
                self.get_data_for_stage_0(
                    room_id,
                    'Привет, я помогу тебе создать задачу в Jira. Нажимай на кнопку "Создать задачу". \
                        Или жми "Начать заново", чтобы сбросить ткущий прогресс создания задачи.',
                ),
            )

        # Стадия 1 - ожидание ввода названия проекта от пользователя
        elif creation_stage == 1:
            jira_client = JiraClient()
            projects = jira_client.get_projects()

            # Бот отправляет в чат список проектов в виде кнопок
            self.send_message(
                self.get_data_for_stage_1(
                    room_id,
                    projects,
                )
            )

            # Перейти на следующую стадию
            self.creation_stage = 2

        # Стадия 1 - ожидание ввода названия задачи от пользователя
        elif creation_stage == 2:
            projects = jira_client.get_projects()

            # Если проект с таким названием существует
            if any(message_text == project.name for project in projects):
                self.send_message(
                    self.get_base_data(
                        room_id, 'Введите название будущей задачи'
                    )
                )
                jira_client.set_project_name(message_text)
                self.creation_stage = 3
            else:
                self.send_message(
                    self.get_base_data(
                        room_id, 'Проект с таким названием не найден.'
                    )
                )

        elif creation_stage == 3:
            issue.set_issue_summary(message_text)
            self.send_message(
                self.get_base_data(
                    room_id, 'Введите описание для будущей задачи'
                )
            )
            self.creation_stage = 4

        # Стадия 4 - создание задачи исходя из полученных данных от пользователя
        elif creation_stage == 4:
            issue.set_issue_description(message_text)
            projects = jira_client.get_projects()

            # Ищем ключ проекта по его названию
            for project in projects:
                if jira_client.get_project_name() == project.name:
                    project_key = project.key
                    break

            # Получаем название задачи
            issue_summary = issue.get_issue_summary()

            # Создаем новую задачу
            jira_client.create_new_issue(
                project_key,
                issue_summary,
                issue.get_issue_description(),
            )

            # Получаем ссылку на задачу
            task_link = jira_client.get_issue_link(project_key, issue_summary)

            self.send_message(
                self.get_base_data(
                    room_id,
                    f'Ваша задача: [клик]({task_link})',
                )
            )

            # Добавляем запись о создании задачи
            models.insert_task_record(user_id, task_link)

            # Все заново
            self.creation_stage = 0

    @catch_exceptions
    def process_messages(self):
        """Обработать новое сообщение"""
        dms = self.get_direct_messages()
        if dms is not None:
            for dm in dms:
                user_id = dm['lastMessage']['u']['_id']
                if 'lastMessage' in dm and user_id != self.bot_id:
                    # Добавляем пользователя чата в БД, если он еще не доабвлен
                    models.insert_new_user(
                        dm['lastMessage']['u']['username'],
                        user_id,
                    )

                    last_msg = dm['lastMessage']
                    message_text = last_msg['msg']
                    room_id = dm['_id']

                    if message_text == 'Создать задачу':
                        self.creation_stage = 1
                    elif message_text == 'Начать заново':
                        self.creation_stage = 0

                    self.go_to_next_stage(
                        self.creation_stage, room_id, message_text, user_id
                    )

    def run(self):
        """Основная функция, отвечающая за запуск бота"""
        self.get_auth_token()
        self.set_status('online')
        while True:
            try:
                self.process_messages()
                time.sleep(1)
            except TimeoutError:
                time.sleep(10)
