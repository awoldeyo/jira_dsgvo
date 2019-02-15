import pandas as pd

from jira.resources import User, CustomFieldOption, Priority, \
                           IssueLink, Issue, Component, Watchers, \
                           Votes, Status, Project, IssueType, \
                           PropertyHolder, Comment, Resolution, Version

class JiraDf(object):
    '''
    Transform a list of JIRA issues to a pandas Dataframe
    
    Parameters
    ----------
    issues : list or jira.client.Resultlist. List should contain JIRA issues.
    
    jira_client : jira.client.JIRA. User interface to JIRA, which was used to create the
    jira.client.Resultlist. Required if frontendcolname=True.
    
    frontendcolname : boolean, default False. If False, the returned dataframe 
    columns will be named according to JIRA backend naming (e.g. customfield_12345). 
    If True, columns will be named according to frontend naming (e.g. Resolution).
    
    stringvalues : boolean, default False. If False the dataframe returned will 
    contain original JIRA datatypes (e.g. User, Component, Issuetype). 
    If True JIRA datatypes will be transformed according to default typeHandler.  
    '''
    
    def __init__(self, issues, jira_client=None, frontendcolname=False, stringvalues=False):
        self.df = to_dataframe(issues)
        self.issues = issues
        self.field = None
        self.col_mapping = None
        self.jira_client = jira_client
        
        if frontendcolname:
            self.setFrontendColname(inplace=True)
        
        if stringvalues:
            self.toStringValue(inplace=True)
    
    def toStringValue(self, inplace=False):
        '''
        Transform JIRA datatypes according to default typeHandler.
        
        Parameters
        ----------
        inplace : boolean, default False. If False will return a transformed
        dataframe. If True will commit changes to self.df.
        '''
        
        if inplace:
            self.df = self.df.applymap(get_string)
        else:
            return self.df.applymap(get_string)
    
    def _getFieldRep(self):
        '''Get field frontend naming from JIRA server.'''
        if self.jira_client:
            self.fields = self.jira_client.fields()
            self.col_mapping = {k['id']:k['name'] for k in self.fields}
        else:
            raise ValueError(f'''Attribute jira_client cannot be {self.jira_client}.''')
    
    def setFrontendColname(self, inplace=False):
        '''
        Rename dataframe columns according to frontend naming.
        
        Parameters
        ----------
        inplace : boolean, default False. If False will return a transformed
        dataframe. If True will commit changes to self.df.
        '''
        
        self._getFieldRep()
        if inplace:
            self.df.columns = self.df.columns.map(lambda x: self.col_mapping.get(x, x))
        else:
            return self.df.columns.rename(index=str, columns=self.col_mapping)


def to_dataframe(issues):
    '''
    Create a pandas dataframe from a list of JIRA issues. By default creates 
    columns for JIRA 'id', 'key' and the JIRA issue object ('issue_object') itself.
    Transforms all JIRA issue fields to dataframe columns.
    
    Parameters
    ----------
    issues : list or jira.client.Resultlist. List should contain JIRA issues.
    '''
    
    df = pd.DataFrame([i.fields.__dict__ for i in issues])
    df['id'] = [i.id for i in issues]
    df['key'] = [i.key for i in issues]
    df['issue_object'] = [i for i in issues]
    return df


def get_string(jira_object):
    '''
    Transforms all original JIRA datatypes according to typeHandler. If not handled
    by typeHandler will return same as input. If input value is None, will return
    None.
    
    Parameters
    ----------
    jira_object : User, CustomField, Priority, etc. 
    '''
    
    def list_handler(jira_object):
        try:
            return "|".join([get_string(o) if o else "" for o in jira_object])
        except TypeError:
            return [get_string(o) if o else "" for o in jira_object]
    
    typeHandler = {
            list: lambda x: list_handler(x),
            str: lambda x: x,
            int: lambda x: x,
            float: lambda x: x,
            dict: lambda x: x,
            pd.Timestamp: lambda x: x,
            User: lambda x: x.displayName,
            CustomFieldOption: lambda x: x.value,
            Priority: lambda x: x.name,
            IssueLink: lambda x: x.id,
            Issue: lambda x: x,
            Component: lambda x: x.name,
            Watchers: lambda x: x.watchCount,
            Votes: lambda x: x.votes,
            Status: lambda x: x.statusCategory.name,
            Project: lambda x: x.key,
            IssueType: lambda x: x.name, 
            PropertyHolder: lambda x: x.__dict__,
            Comment: lambda x: x.body,
            Resolution: lambda x: x.name,
            Version: lambda x: x.name,
            }
    
    if jira_object:
        try:
            return typeHandler[type(jira_object)](jira_object)
        except KeyError:
            print(f"{type(jira_object)} does not exist")
            return jira_object
    else:
        return
