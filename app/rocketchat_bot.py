import requests
import time
import logging
from jira_client import JiraClient


def catch_exceptions(func):
    """Обработка исключений"""

    def wrapper(*args, **kwargs):
        try:
            return func(*args, **kwargs)
        except requests.exceptions.RequestException as ex:
            logging.exception(f'Возникло исключение: {ex}')

    return wrapper


# Экземпляр класса JiraClient
jira_client = None


class RocketChatBot:

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
        login_url = self.base_url + 'login'
        data = {'user': self.username, 'password': self.password}
        response = requests.post(login_url, json=data)
        response.raise_for_status()
        self.auth_token = response.json()['data']['authToken']

    @catch_exceptions
    def set_status(self, status_name):
        """Задать статус боту"""
        set_status_url = self.base_url + 'users.setStatus'
        headers = {
            'X-Auth-Token': self.auth_token,
            'X-User-Id': self.bot_id,
            'Content-Type': 'application/json',
        }
        status_data = {'status': status_name}
        requests.post(set_status_url, headers=headers, json=status_data)

    @catch_exceptions
    def send_message(self, data):
        """Отправить сообщения в чат"""
        send_msg_url = self.base_url + 'chat.postMessage'
        headers = {
            'X-Auth-Token': self.auth_token,
            'X-User-Id': self.bot_id,
        }

        requests.post(send_msg_url, headers=headers, json=data)

    @catch_exceptions
    def get_direct_messages(self):
        """Получить список сообщений"""
        dm_url = self.base_url + 'im.list'
        headers = {
            'X-Auth-Token': self.auth_token,
            'X-User-Id': self.bot_id,
        }
        response = requests.get(dm_url, headers=headers)
        response.raise_for_status()
        dms = response.json()['ims']
        return dms

    def get_data_for_stage_0(self, room_id, message):
        return {
            'channel': room_id,
            'text': message,
            'attachments': [
                {
                    'color': '#FFFFFF',
                    'text': ' ',
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
                }
            ],
        }

    def get_base_data(self, room_id, message):
        """Получить базовое JSON-представление из id комнаты и сообщения"""
        return {'roomId': room_id, 'text': message}

    @catch_exceptions
    def go_to_next_stage(self, creation_stage, room_id, message_text):
        """Логика переходов между этапы создания задачи"""
        global jira_client
        if creation_stage == 0:
            self.send_message(
                self.get_data_for_stage_0(
                    room_id,
                    'Привет, я помогу тебе создать задачу в Jira. Нажимай на кнопку "Создать задачу".',
                ),
            )
        # Стадия 1 - ожидание ввода названия проекта от пользователя
        elif creation_stage == 1:
            jira_client = JiraClient()
            # jira_client.set_projects(jira_client.get_init_projects())
            projects = jira_client.get_projects()

            project_list = '\n'.join([project.name for project in projects])
            # Преобразовываем список в строку, разделяя названия проектов переводом строки
            self.send_message(
                self.get_base_data(
                    room_id, 'Список доступных проектов:\n' + project_list
                )
            )
            self.send_message(
                self.get_base_data(
                    room_id,
                    'Напишите название проекта, для которого нужно создать задачу',
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
                        room_id, 'Введите название для будущей задачи'
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
                self.creation_stage = 0

        # Стадия 3 - создание задачи исходя изполученных данных от пользователя
        elif creation_stage == 3:
            projects = jira_client.get_projects()

            for project in projects:
                if jira_client.get_project_name() == project.name:
                    project_key = project.key
                    break
            jira_client.create_new_issue(project_key, message_text)

            self.send_message(
                self.get_base_data(
                    room_id,
                    f'Ваша задача: [клик]({jira_client.get_issue_link(project_key, message_text)})',
                )
            )
            self.creation_stage = 0

    @catch_exceptions
    def process_messages(self):
        """Обработать новое сообщение"""
        dms = self.get_direct_messages()
        for dm in dms:
            if (
                'lastMessage' in dm
                and dm['lastMessage']['u']['_id'] != self.bot_id
            ):

                last_msg = dm['lastMessage']
                message_text = last_msg['msg']
                room_id = dm['_id']

                if message_text == 'Создать задачу':
                    self.creation_stage = 1

                self.go_to_next_stage(
                    self.creation_stage, room_id, message_text
                )

    def run(self):
        """Основная функция, отвечающая за запуск бота"""
        self.get_auth_token()
        self.set_status('online')
        while True:
            self.process_messages()
            time.sleep(1)
