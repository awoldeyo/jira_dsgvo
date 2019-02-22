import pandas as pd
from pandas.errors import OutOfBoundsDatetime

from cocoa import Connection
from format_df import JiraDf


def to_datetime(string):
    '''Checks if date is valid. Returns None in case of invalid date.'''
    try:
        return pd.to_datetime(string, dayfirst=True)
    except OutOfBoundsDatetime as o:
        return None

def get_changelog(project_issues):
    '''
       Returns information on when due date/due date implemented
       was changed. For changes before 30.10.2018 only the 
       due date field is considered, for every change after 
       30.10.2018 only due date implemented field is considered.
    '''
    duedate = []
    for issue in project_issues:
        changelog = issue.changelog
        for history in changelog.histories:
            for item in history.items:
                created_dt = pd.to_datetime(history.created, dayfirst=True)
                is_before_change = created_dt <= pd.to_datetime('30.10.2018')
                if is_before_change and item.field == "duedate":
                    row = {}
                    row['id'] = issue.id
                    row['date'] = to_datetime(history.created)
                    row['from'] = to_datetime(item.fromString)
                    row['to'] = to_datetime(item.toString)
                    duedate.append(row)
                if item.field == "Due Date Implemented":
                    row = {}
                    row['id'] = issue.id
                    row['date'] = to_datetime(history.created)
                    row['from'] = to_datetime(item.fromString)
                    row['to'] = to_datetime(item.toString)
                    duedate.append(row)
    return pd.DataFrame(duedate)


def create_datetable(df):
    '''
       Returns a reshaped changelog dataframe, so that every row
       becomes a separate column ('Due Date 1', 'Due Date 2', etc.).
    '''
    df = df.sort_values(['id', 'date'], ascending=False)
    df = df.set_index('id').sort_values(['id', 'date'], ascending=True)
    
    # Calculate the maximum required number of columns
    cols = df.groupby('id').count()['date'].max()
    # Define name of columns ("Due Date 1", "Due Date 2", etc.)
    col_names = [f'Due Date {i+1}' for i in range(cols)]

    table = []
    for idx in df.index.unique():
        row = {}
        row['id'] = idx
        for n,date in enumerate(df.loc[[idx], 'to'].sort_values(ascending=True).drop_duplicates()):
            row[col_names[n]] = date
        table.append(row)
    return pd.DataFrame(table).set_index('id')


jira = Connection().jira

issues_in_project = jira.search_issues(
        jql_str='project = DC AND labels in (VW-PKW, VW-PKW_InKlaerungKILX)',
        maxResults=False,
        expand='changelog')

duedate = get_changelog(issues_in_project)
duedate_dt = create_datetable(duedate)

issues_df = JiraDf(issues=issues_in_project, 
                   jira_client=jira, 
                   frontendcolname=True, 
                   stringvalues=True).df

issues_df.columns = [c.title() if c =='status' else c for c in issues_df.columns]
cols = ['id',
        'key',
        'Department',
        'Component/s',
        'Detailed Type',
        'Assignee',
        'Contact Person (Business department)',
        'Contact Person (IT)',
        'Business Transaction',
        'Affected IT-System',
        'Summary',
        'Status',
        'Handover Date',
        'Dokumente vorhanden?'
       ]

issues_df.dropna(axis=1, how='all', inplace=True)
issues_df = issues_df.reindex(cols, axis=1)

new_colname = ['id','JIRA ID', 'Bereich', 'Component/s', 'Detailed Type', 'Assignee',
       'Contact Person (Business department)', 'Contact Person (IT)',
       'Business Transaction', 'System', 'Maßnahme', 'Status',
       'Maßnahme übergeben am:', 'Dokumente vorhanden?']
issues_df.columns = new_colname
issues_df.fillna('', inplace=True)

final_df = pd.merge(issues_df, duedate_dt, on='id')
final_df = final_df.drop('id', axis=1).fillna('')
date_time_cols = [c for c in final_df.columns if 'date' in c.lower()]
date_time_cols += ['Maßnahme übergeben am:']
final_df[date_time_cols] = final_df[date_time_cols].apply(lambda x: pd.to_datetime(x, dayfirst=True))
today = pd.datetime.today().strftime('%d_%m_%Y')
final_df.to_excel(f'Eskalationstracking_JIRA_py_export_{today}.xlsx', index=False, sheet_name='Maßnahmen')
