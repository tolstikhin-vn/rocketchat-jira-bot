import json
import logging
from typing import Any, List, Dict, Optional
from jira import JIRA


class JiraClient:
    """Класс для работы с Jira"""

    def __init__(self):
        self.jira: Optional[JIRA] = None
        self.project_name: Optional[str] = None

    def connect(self):
        """Подключиться к серверу Jira"""
        try:
            with open('src/data/config_jira.json') as jira_config_file:
                jira_config: Dict[str, Any] = json.load(jira_config_file)
                url: str = jira_config['url']
                jira_token: str = jira_config['jira_token']
                self.jira = JIRA(server=url, token_auth=jira_token)
        except FileNotFoundError:
            logging.error('Ошибка: файл config_jira.json не найден.')
        except json.JSONDecodeError:
            logging.error(
                'Ошибка: некорректный формат JSON в файле config_jira.json.'
            )
        except Exception as ex:
            logging.exception(f'Ошибка при подключении к серверу Jira: {ex}')

    def get_data_for_issue(
        self, project_key: str, summary: str, description: str
    ) -> Dict[str, Any]:
        """Получить JSON-представление для создания задачи"""
        return {
            'project': {'key': project_key},
            'summary': summary,
            'description': description,
            'issuetype': {'name': 'Task'},
        }

    def get_projects(self) -> List[Any]:
        """Получить список проектов из результатов запроса к серверу"""
        try:
            if not self.jira:
                self.connect()
            return self.jira.projects()
        except Exception as ex:
            logging.exception(f'Ошибка при получении списка проектов: {ex}')
            return []

    def create_new_issue(
        self, project_key: str, summary: str, description: str
    ):
        """Создать задачу в проекте"""
        try:
            if not self.jira:
                self.connect()
            self.jira.create_issue(
                fields=self.get_data_for_issue(
                    project_key, summary, description
                )
            )
        except Exception as ex:
            logging.exception(f'Ошибка при создании задачи: {ex}')

    def get_issue_link(
        self, project_key: str, issue_summary: str
    ) -> Optional[str]:
        """Запрос на поиск задач с указанным названием в проекте"""
        try:
            issues = self.jira.search_issues(
                f'project={project_key} AND summary~"{issue_summary}"'
            )
            # Проверка, найдены ли задачи
            if len(issues) > 0:
                # Получение ключа последней найденной задачи
                last_issue = max(issues, key=lambda issue: int(issue.id))
                issue_key = last_issue.key
                return f'{self.jira.server_url}/browse/{issue_key}'
        except Exception as ex:
            logging.exception(f'Ошибка при получении ссылки на задачу: {ex}')
        return None

    def get_project_name(self) -> None:
        """Получить название проекта"""
        return self.project_name

    def set_project_name(self, project_name) -> None:
        """Установить название проекта, чтобы в дальнейшем его использовать"""
        self.project_name = project_name


class Issue:
    """Класс для представления задачи"""

    def __init__(self):
        self.issue_summary = None
        self.issue_description = None

    def get_issue_summary(self):
        return self.issue_summary

    def set_issue_summary(self, issue_summary):
        self.issue_summary = issue_summary

    def get_issue_description(self):
        return self.issue_description

    def set_issue_description(self, issue_description):
        self.issue_description = issue_description
