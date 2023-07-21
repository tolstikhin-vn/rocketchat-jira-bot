import json
import logging
import threading
import database

from jira import Project
from typing import Any, List, Tuple, Set, Dict, Optional
from fastapi import FastAPI, Request
from fastapi.responses import HTMLResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
import uvicorn

from jira_client import JiraClient
from rocketchat_bot import RocketChatBot

OFFLINE_STATUS: str = 'offline'

app: FastAPI = FastAPI()
templates: Jinja2Templates = Jinja2Templates(directory='src/templates')
app.mount(
    '/static', StaticFiles(directory='src/static', html=True), name='static'
)


@app.get('/logs', response_class=HTMLResponse)
def get_logs(
    request: Request,
    project_id: Optional[int] = None,
    startDate: Optional[str] = None,
    endDate: Optional[str] = None,
):
    """Обработчик GET-запросов для отображения логов созданных задач"""
    try:
        logs: List[int] = []
        if project_id is not None:
            logs = database.get_logs(project_id, startDate, endDate)
            logs_data: List[Dict[str, Any]] = [
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

        jira_client: JiraClient = JiraClient()
        projects: List[Project] = jira_client.get_projects()
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


def load_uvicorn_conf() -> Tuple[str, int]:
    """Загрузка параметров host и port из конфигурационного файла."""
    try:
        with open('src/data/config_uvicorn.json') as app_json_file:
            config_uvicorn: Dict[str, Any] = json.load(app_json_file)

        host = config_uvicorn['host']
        port = config_uvicorn['port']
        return host, port

    except FileNotFoundError as ex1:
        raise Exception(f'Не удалось найти конфигурационный файл: {ex1}')

    except json.JSONDecodeError as ex2:
        raise Exception(f'Ошибка декодирования JSON: {ex2}')

    except Exception as ex3:
        raise Exception(f'Возникло исключение: {ex3}')


def run_bot() -> None:
    try:
        with open('src/data/config_bot.json') as rc_json_file:
            config_rc: Dict[str, str] = json.load(rc_json_file)

        # Получить параметры аутентификации для работы с ботом
        base_url: str = config_rc['base_url']
        username: str = config_rc['username']
        password: str = config_rc['password']
        bot_id: str = config_rc['bot_id']

        bot: RocketChatBot = RocketChatBot(
            base_url, username, password, bot_id
        )

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

        host, port = load_uvicorn_conf()

        uvicorn.run(app, host=host, port=port)
    except Exception as ex:
        logging.exception(f'Возникло исключение: {ex}')
