import requests
import pandas as pd
from pandas.tseries.offsets import BDay

from cocoa import Connection
from format_df import JiraDf

# =============================================================================
# Set the concept legally approved date to date of implementation + 15 business days
# =============================================================================

jira = Connection()
cookies = jira.cookies
jira = jira.jira

jql_str = '''project = DC 
             AND labels in (VW-PKW, VW-PKW_InKlaerungKILX) 
             AND "Detailed Type" not in (V:ADV, T:Beauskunftung) 
             AND status = Implemented'''

print('Collecting JIRA issues ...')

issues_in_project = jira.search_issues(
        jql_str=jql_str, 
        maxResults=False, 
        expand='changelog'
        )

print(f'Collected {len(issues_in_project)} issues for which status is implemented.')

df = JiraDf(
        jira_client=jira, 
        frontendcolname=True, 
        issues=issues_in_project,
        stringvalues=True, 
        changelog=True
        ).df

df = df[df['to'] == 'Implemented']
df['date'] = pd.to_datetime(df.date, dayfirst=True).copy()
df.sort_values('date', ascending=False, inplace=True)
df.drop_duplicates(subset=['id'], keep='first', inplace=True)
df.loc[:, 'concept_legally_approved'] = df.date.map(lambda x: x + BDay(15))
df['concept_legally_approved'] = df.concept_legally_approved.map(lambda x: x.strftime('%Y-%m-%d'))
date_mismatch = df['concept_legally_approved'] != df['Due Date Concept legally approved']

issue_keys = ',\n'.join(df.loc[date_mismatch,'key'].tolist())
commit = input(f"The Concept legally approved date for the following issues needs\
               to be updated:\n\
               {issue_keys} \nTo update date, enter y(es) or n(o): ")

if commit == 'y':
    df.loc[date_mismatch,:].apply(lambda x: x['issue_object'].update(
        fields={'customfield_13713':x['concept_legally_approved']}, 
        notify=False
        ), axis=1)
    
    print(f'Updated Concept legally approved date for \
      {df.loc[date_mismatch,:].shape[0]} issues.')

    reportlink_24391 = "https://cocoa.volkswagen.de/sjira/sr/jira.issueviews:\
    searchrequest-excel-current-fields/24391/SearchRequest-24391.xls"
    
    with requests.Session() as s:
        excel = s.get(reportlink_24391, cookies=cookies)
    
    with open('Concept Legally approved.xls', mode='w') as f:
        f.write(excel.text)
    
elif commit=='n':
    print('No changes made!')
else:
    print('Did not understand input. No changes made.')

# =============================================================================
# Get reports from favourite filters
# =============================================================================
    
favourite_filters = jira.favourite_filters()

for fav_filter in favourite_filters:
    with requests.Session() as s:
        reportlink = f'https://cocoa.volkswagen.de/sjira/sr/jira.issueviews:searchrequest-excel-current-fields/{fav_filter.id}/SearchRequest-{fav_filter.id}.xls'
        excel = s.get(reportlink, cookies=cookies)
    with open(f'{fav_filter.name}.xls', mode='w') as f:
        f.write(excel.text)