import json
from jira import JIRA


class JiraClient:
    def __init__(self):
        self.jira = None
        self.project_name = None

    def connect(self):
        """Подключиться к серверу Jira"""
        with open('data/config_jira.json') as jira_config_file:
            jira_config = json.load(jira_config_file)
            url = jira_config['url']
            jira_token = jira_config['jira_token']
            self.jira = JIRA(server=url, token_auth=jira_token)

    def get_data_for_issue(self, project_key, summary, description):
        """Получить JSON-представление для создания задачи"""
        return {
            'project': {'key': project_key},
            'summary': summary,
            'description': description,
            'issuetype': {'name': 'Task'},
        }

    def get_projects(self):
        """Получить список проектов из результатов запроса к серверу"""
        if not self.jira:
            self.connect()
        return self.jira.projects()

    def create_new_issue(self, project_key, summary, description):
        """Создать задачу в проекте"""
        if not self.jira:
            self.connect()
        self.jira.create_issue(
            fields=self.get_data_for_issue(project_key, summary, description)
        )

    def get_issue_link(self, project_key, issue_summary):
        # Запрос на поиск задач с указанным названием в проекте
        issues = self.jira.search_issues(
            f'project={project_key} AND summary~"{issue_summary}"',
            maxResults=1,
        )
        # Проверка, найдены ли задачи
        if len(issues) > 0:
            # Получение ключа последней найденной задачи
            issue_key = issues[-1].key
            return f'{self.jira.server_url}/browse/{issue_key}'

    def get_project_name(self):
        return self.project_name

    def set_project_name(self, project_name):
        self.project_name = project_name


class Issue:
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
