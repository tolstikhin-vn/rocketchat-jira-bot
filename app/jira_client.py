from jira import JIRA
import json


class JiraClient:
    def __init__(self):
        self.jira = None

    def connect(self):
        """Подключение к Jira"""
        with open('data/connection_jira.json') as jira_config_file:
            jira_config = json.load(jira_config_file)
            url = jira_config['url']
            username = jira_config['username']
            password = jira_config['password']
            self.jira = JIRA(server=url, basic_auth=(username, password))

    def get_projects(self):
        """Получение списка проектов"""
        print('тут')
        if not self.jira:
            self.connect()
            projects = self.jira.projects()
            project_names = [project.name for project in projects]
            return project_names
