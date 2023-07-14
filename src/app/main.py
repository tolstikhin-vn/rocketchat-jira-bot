import json
import logging
import threading
import database

from fastapi import FastAPI, Request
from fastapi.responses import HTMLResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from typing import Optional
import uvicorn

from jira_client import JiraClient
from rocketchat_bot import RocketChatBot

OFFLINE_STATUS = 'offline'

app = FastAPI()
templates = Jinja2Templates(directory='src/templates')
app.mount(
    '/static', StaticFiles(directory='src/static', html=True), name='static'
)


@app.get('/logs', response_class=HTMLResponse)
def get_logs(
    request: Request,
    project_id: Optional[int] = None,
    date: Optional[str] = None,
):
    """Обработчик GET-запросов для отображения логов созданных задач"""
    try:
        logs = []
        if project_id is not None:
            logs = database.get_logs(project_id, date)
            logs_data = [
                {
                    'user_name': user_name,
                    'user_id': user_id,
                    'task_link': log.task_link,
                    'task': log.task_link.split('browse/')[-1],
                    'datetime_creating': log.datetime_creating.strftime(
                        '%Y-%m-%d %H:%M:%S'
                    ),
                }
                for log, user_name, user_id in logs
            ]
            return json.dumps(logs_data)

        jira_client = JiraClient()
        projects = jira_client.get_projects()
        return templates.TemplateResponse(
            'index.html',
            {'request': request, 'logs': logs, 'projects': projects},
        )
    except database.DatabaseError as ex1:
        logging.exception(f'Произошла ошибка базы данных: {ex1}')

    except jira_client.JiraError as ex2:
        logging.exception(f'Произошла ошибка Jira: {ex2}')

    except Exception as ex3:
        logging.exception(f'Возникло исключение: {ex3}')


def run_bot():
    try:
        with open('src/data/config_bot.json') as rc_json_file:
            config_rc = json.load(rc_json_file)

        # Получить параметры аутентификации для работы с ботом
        base_url = config_rc['base_url']
        username = config_rc['username']
        password = config_rc['password']
        bot_id = config_rc['bot_id']

        bot = RocketChatBot(base_url, username, password, bot_id)

        # Запуск бота
        bot.run()
    except FileNotFoundError as ex1:
        logging.exception(f'Не удалось найти конфигурационный файл: {ex1}')

    except json.JSONDecodeError as ex2:
        logging.exception(f'Ошибка декодирования JSON: {ex2}')

    except Exception as ex3:
        logging.exception(f'Возникло исключение: {ex3}')

    finally:
        bot.set_status(OFFLINE_STATUS)


if __name__ == '__main__':
    try:
        bot_thread = threading.Thread(target=run_bot)
        bot_thread.start()

        uvicorn.run(app, host='127.0.0.1', port=8000)
    except Exception as ex:
        logging.exception(f'Возникло исключение: {ex}')
