import json
from rocketchat_bot import RocketChatBot

if __name__ == '__main__':
    with open('data/connection_bot.json') as file:
        config = json.load(file)

    base_url = config['base_url']
    username = config['username']
    password = config['password']
    bot_id = config['bot_id']

    bot = RocketChatBot(base_url, username, password, bot_id)
    bot.main()
