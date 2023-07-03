import requests
import json


def catch_exceptions(func):
    """Обработка исключений"""

    def wrapper(*args, **kwargs):
        try:
            return func(*args, **kwargs)
        except requests.exceptions.RequestException as ex:
            print(f'Возникла ошибка: {ex}')

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
            if 'lastMessage' in dm:
                last_msg = dm['lastMessage']
                if 'u' in last_msg and 'username' in last_msg['u']:
                    message_text = last_msg['msg']
                    room_id = dm['_id']

                    if message_text == 'start':
                        self.send_message(
                            room_id,
                            'Привет, я бот-помощник для автоматизации с Jira. Напиши мне свою проблему или задачу.',
                        )

    def main(self):
        """Основная функция, выполняющая запуск бота на получение сообщений"""
        self.get_auth_token()
        self.set_status('online')
        while True:
            self.process_messages()


if __name__ == '__main__':
    with open('data/connection_bot.json') as file:
        config = json.load(file)

    base_url = config['base_url']
    username = config['username']
    password = config['password']
    bot_id = config['bot_id']

    bot = RocketChatBot(base_url, username, password, bot_id)

    bot.main()
