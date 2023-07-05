import json
from rocketchat_bot import RocketChatBot

if __name__ == '__main__':
    with open('data/config_bot.json') as rc_json_file:
        config_rc = json.load(rc_json_file)

    # Получить параметры аутентификации для работы с ботом
    base_url = config_rc['base_url']
    username = config_rc['username']
    password = config_rc['password']
    bot_id = config_rc['bot_id']

    bot = RocketChatBot(base_url, username, password, bot_id)

    # Запуск бота
    bot.run()
