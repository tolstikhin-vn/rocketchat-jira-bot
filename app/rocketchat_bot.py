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


class RocketChatBot:
    def __init__(self, base_url, username, password, bot_id):
        self.base_url = base_url
        self.username = username
        self.password = password
        self.bot_id = bot_id
        self.auth_token = None

    @catch_exceptions
    def get_auth_token(self):
        """Получение токена авторизации пол логину и паролю бота-пользователя"""
        login_url = self.base_url + 'login'
        data = {'user': self.username, 'password': self.password}
        response = requests.post(login_url, json=data)
        response.raise_for_status()
        self.auth_token = response.json()['data']['authToken']

    @catch_exceptions
    def set_status(self, status_name):
        """Установка статуса бота"""
        set_status_url = self.base_url + 'users.setStatus'
        headers = {
            'X-Auth-Token': self.auth_token,
            'X-User-Id': self.bot_id,
            'Content-Type': 'application/json',
        }
        status_data = {'status': status_name}
        requests.post(set_status_url, headers=headers, json=status_data)

    @catch_exceptions
    def send_message(self, room_id, message):
        """Отправка сообщения"""
        send_msg_url = self.base_url + 'chat.postMessage'
        headers = {
            'X-Auth-Token': self.auth_token,
            'X-User-Id': self.bot_id,
        }
        data = {'roomId': room_id, 'text': message}
        requests.post(send_msg_url, headers=headers, json=data)

    # @catch_exceptions
    # def delete_message(self, message_id):
    #     """Удаление сообщения по ID"""
    #     delete_msg_url = self.base_url + 'chat.delete'
    #     headers = {
    #         'X-Auth-Token': self.auth_token,
    #         'X-User-Id': self.bot_id,
    #     }
    #     data = {'roomId': message_id}
    #     requests.post(delete_msg_url, headers=headers, json=data)

    @catch_exceptions
    def send_message_with_button(self, room_id, message):
        """Отправка сообщения"""
        send_msg_url = self.base_url + 'chat.postMessage'
        headers = {
            'X-Auth-Token': self.auth_token,
            'X-User-Id': self.bot_id,
        }
        data = {
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
        requests.post(send_msg_url, headers=headers, json=data)

    @catch_exceptions
    def get_direct_messages(self):
        """Получение списка сообщений"""
        dm_url = self.base_url + 'im.list'
        headers = {
            'X-Auth-Token': self.auth_token,
            'X-User-Id': self.bot_id,
        }
        response = requests.get(dm_url, headers=headers)
        response.raise_for_status()
        dms = response.json()['ims']
        return dms

    @catch_exceptions
    def process_messages(self):
        """Обработка сообщений"""
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
                    # JiraClient.connect()
                    jira_client = JiraClient()
                    projects = jira_client.get_projects()
                    project_list = '\n'.join(projects)
                    # Преобразовываем список в строку, разделяя названия проектов переводом строки
                    self.send_message(
                        room_id, 'Список проектов в Jira:\n' + project_list
                    )

                    self.send_message(room_id, 'Введите название проекта:')
                    # self.delete_message(last_msg['_id'])
                else:
                    self.send_message_with_button(
                        room_id,
                        'Привет, я помогу тебе создать задачу в Jira. Нажимай на кнопку "Создать задачу".',
                    )

    def run(self):
        """Основная функция, выполняющая запуск бота на получение сообщений"""
        self.get_auth_token()
        self.set_status('online')
        while True:
            self.process_messages()
            time.sleep(1)
