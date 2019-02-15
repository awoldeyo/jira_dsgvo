import requests
import getpass
from jira.client import JIRA
from json import JSONDecodeError


class Connection(object):
    '''Instantiate a JIRA client object to www.cocoa.volkswagen.de'''
    def __init__(self):
        self.url = 'https://cocoa.volkswagen.de/sjira/'
        self.cookies = self.authenticate()
        self.jira = self.client()
    
    def authenticate(self):
        '''Authenticates user and gets session cookie.'''
        with requests.Session() as s:
            credentials = {}
            credentials['username'] = input("Enter your username: ")
            credentials['password'] = getpass.getpass("Enter your password: ")
            credentials['login-form-type'] = 'token'
            s.post('https://cocoa.volkswagen.de/pkmslogin.form', data=credentials)
            
        if s.cookies:
            print(f'Login successful!')
            return s.cookies 
        else:
            print(f'Login failed! Please check username and/or password.')
            return s.cookies
                
    def client(self):
        '''Creates JIRA client object or returns None if failed.'''
        try:
            jira_options={'server': self.url, 'cookies':self.cookies}
            jira=JIRA(options=jira_options, async_=True, async_workers=8)
            print(f'You are logged in as {jira.current_user()}!')
            return jira
        except JSONDecodeError as j:
            print(j)
            return