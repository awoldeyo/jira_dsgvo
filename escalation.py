from optparse import OptionParser

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
    
    # Split dataframe into two dataframes (from & to)
    df_from = df.loc[:, ['id', 'date', 'from']]
    df_to = df.loc[:, ['id', 'date', 'to']]
    
    # Name both dataframes' columns identical and concatenate both
    df_from.columns = ['id', 'date', 'value']
    df_to.columns = ['id', 'date', 'value']
    df = pd.concat((df_to, df_from))
    
    # Sort table and drop duplicates (keep most recent changes) and na values
    df.sort_values(['id', 'date', 'value'], ascending=True, inplace=True)
    df.drop_duplicates(subset=['id', 'value'] , keep='first', inplace=True)
    df.dropna(axis=0, how='any', inplace=True)
    df = df.set_index('id').sort_values(['id', 'date'], ascending=True)
    
    # Calculate the maximum required number of columns
    cols = df.groupby('id').count()['date'].max()
    # Define name of columns ("Due Date 1", "Due Date 2", etc.)
    col_names = [f'Due Date {i+1}' for i in range(cols)]

    table = []
    for idx in df.index.unique():
        row = {}
        row['id'] = idx
        for n,date in enumerate(df.loc[[idx], 'value'].sort_values(ascending=True).drop_duplicates()):
            row[col_names[n]] = date
        table.append(row)
    datetable = pd.DataFrame(table).set_index('id')
    
    return datetable


parser = OptionParser()
args = parser.add_option("-c", action="store_true", dest="stored", help="Use stored cookie to authenticate.")
(options, args) = parser.parse_args()
jira = Connection(stored_cookie=options.stored).jira

print('Collecting JIRA issues ...')

issues_in_project = jira.search_issues(
        jql_str='project = DC AND labels in (VW-PKW, VW-PKW_InKlaerungKILX)',
        maxResults=False,
        expand='changelog')

print(f'Collected {len(issues_in_project)}.')

duedate = get_changelog(issues_in_project)
duedate_reshaped = create_datetable(duedate)

issues_df = JiraDf(issues=issues_in_project, 
                   jira_client=jira, 
                   frontendcolname=True, 
                   stringvalues=True).df

issues_df.dropna(axis=1, how='all', inplace=True)                   
                   
issues_df.columns = [c.title() if c =='status' else c for c in issues_df.columns]
cols = [
        'id',
        'key',
        'Department',
        'Component/s',
        'Detailed Type',
        'Reporter',
        'Assignee',
        'Contact Person (Business department)',
        'Contact Person (IT)',
        'Business Transaction',
        'Affected IT-System',
        'Summary',
        'Status',
        'Handover Date',
        'Dokumente vorhanden?',
        'Due Date Implemented'
        ]

issues_df = issues_df.reindex(cols, axis=1)

new_colname = [
        'id',
        'JIRA ID', 
        'Bereich', 
        'Component/s', 
        'Detailed Type', 
        'Reporter',
        'Assignee', 
        'Contact Person (Business department)', 
        'Contact Person (IT)',
        'Business Transaction', 
        'System', 
        'Maßnahme', 
        'Status',
        'Maßnahme übergeben am:', 
        'Dokumente vorhanden?',
        'Due Date Implemented'
        ]
issues_df.columns = new_colname
issues_df.fillna('', inplace=True)

# Create Hyperlinks in column JIRA DF
url = 'https://cocoa.volkswagen.de/sjira/browse/'
create_url = lambda x: f'=HYPERLINK("{url}{x}", "{x}")'
issues_df['JIRA ID'] = issues_df['JIRA ID'].map(create_url)

# Merge duedate changelog and issues dataframe
final_df = pd.merge(issues_df, duedate_reshaped, how='outer', on='id')

# Set Due Date 1 to Due date implemented for never changed due dates
no_changelog = issues_df.loc[issues_df['id'].isin(duedate_reshaped.index)==False, 'id']
duedate_never_changed = final_df['id'].isin(no_changelog)
final_df.loc[duedate_never_changed, 'Due Date 1'] = final_df.loc[duedate_never_changed, 'Due Date Implemented']
final_df.drop('Due Date Implemented', axis=1, inplace=True)

# Clean up final dataframe
final_df = final_df.drop('id', axis=1).fillna('')
date_time_cols = [c for c in final_df.columns if 'date' in c.lower()]
date_time_cols += ['Maßnahme übergeben am:']

final_df[date_time_cols] = final_df[date_time_cols].apply(lambda x: pd.to_datetime(x, dayfirst=True))
today = pd.datetime.today().strftime('%d_%m_%Y')
final_df.to_excel(f'Eskalationstracking_JIRA_py_export_{today}.xlsx', index=False, sheet_name='Maßnahmen')
