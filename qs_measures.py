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
             AND status = Implemented 
             AND "Due Date Concept legally approved" is EMPTY'''

issues_in_project = jira.search_issues(
        jql_str=jql_str, 
        maxResults=False, 
        expand='changelog'
        )

print(f'There are currently {len(issues_in_project)} issues for which the \
                             Concept legally approved date needs to be updated.')

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
df.apply(lambda x: x['issue_object'].update(
        fields={'customfield_13713':x['concept_legally_approved']}, 
        notify=False
        ), axis=1)

reportlink_24391 = "https://cocoa.volkswagen.de/sjira/sr/jira.issueviews:\
searchrequest-excel-current-fields/24391/SearchRequest-24391.xls"

with requests.Session() as s:
    excel = s.get(reportlink_24391, cookies=cookies)

with open('Concept Legally approved.xls', mode='w') as f:
    f.write(excel.text)
