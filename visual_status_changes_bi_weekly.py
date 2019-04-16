import pandas as pd
from pandas.tseries.offsets import Day
from pandas.api.types import CategoricalDtype
from jira.client import JIRA

import plotly.plotly as py
import plotly.graph_objs as go
from plotly.offline import init_notebook_mode, iplot, plot


from format_df import JiraDf
from cocoa import Connection

init_notebook_mode(connected=True)

# Authentication:
try:
    # First try to connect with existing cookie
    jira = Connection(stored_cookie=True, 
                      async_=False, 
                      async_workers=None).jira
    if not isinstance(jira, JIRA):
        raise ValueError
except (ValueError, FileNotFoundError):
    # If cookie expired request username and password
    jira = Connection().jira

issues_in_project = jira.search_issues(jql_str='project = DC AND labels in (VW-PKW, VW-PKW_InKlaerungKILX)', 
                                       maxResults=False, 
                                       expand='changelog')

df = JiraDf(issues=issues_in_project, 
            jira_client=jira, 
            frontendcolname=True, 
            stringvalues=True, 
            changelog=True).df

df.dropna(axis=1, how='all', inplace=True)

df['date'] = pd.to_datetime(df['date'])
df['Created'] = pd.to_datetime(df['Created'])

cols = ['key',
        'Summary',
        'Affected IT-System',
        'Business Transaction',
        'Technical implementation needed',
        'Reporter',
        'Assignee',
        'Department',
        'Contact Person (Business department)',
        'Contact Person (IT)',
        'Component/s',
        'Status',
        'Created',
        'author',
        'date',
        'from',
        'to'
       ]

df_new_cols = df.loc[:, cols].copy(True)

sorter = ['Draft',
          'Order approval',
          'Concept Decision',
          'Design Decision',
          'Implemented',
          'Concept legally approved',
          'Technical Implementation Started',
          'Resolved',
          'Closed'
         ]
cat_type = CategoricalDtype(categories=sorter,
                            ordered=True)

data_df = df_new_cols.copy(True)

data_df['from'] = data_df['from'].astype(cat_type)
data_df['to'] = data_df['to'].astype(cat_type)

data_df.sort_values(['key', 'date'], ascending=False, inplace=True)

draft = data_df.drop_duplicates(subset='key', keep='first').loc[:, ['key', 'Created', 'Status']].set_index('key').copy(True)
draft.columns = ['Date', 'Status_final']
draft['Status'] = 'Draft'
draft['Status'] = draft['Status'].astype(cat_type)
draft = draft.reindex(columns=['Date', 'Status', 'Status_final'])

status_changes = data_df.loc[:, ['key', 'date', 'to', 'Status']].copy(True)
status_changes.set_index('key', inplace=True)
status_changes.columns = ['Date', 'Status', 'Status_final']
status_changes = pd.concat((status_changes, draft), axis=0)
status_changes.sort_values(['key','Date'], ascending=False, inplace=True)
status_changes = status_changes.assign(Date=status_changes.Date.dt.date)
status_changes.reset_index(inplace=True)
status_changes.drop_duplicates(subset=['key', 'Date'], inplace=True)
status_changes['Date'] = pd.to_datetime(status_changes['Date'])

fourteen_days_ago = pd.datetime.today() - Day(14)
date_range = (status_changes['Date']<=fourteen_days_ago)

before_status = status_changes[date_range].drop_duplicates(subset=['key']).copy(True)
after_status = status_changes.drop_duplicates(subset=['key']).copy(True)
after_status['Status_final'] = after_status.Status_final.astype(cat_type)

transitions = pd.merge(left=before_status, 
                       right=after_status, 
                       how='outer', 
                       on='key', 
                       suffixes=('_before', '_after')).reindex(columns=['key', 
                                                                        'Status_before', 
                                                                        'Status_final_after']
                                                              ).copy(True)

transitions.loc[transitions.Status_before.isna(), 'Status_before'] = 'Draft'

no_changes = (transitions.Status_before==transitions.Status_final_after)
forward = (transitions.Status_before<transitions.Status_final_after)
backward = (transitions.Status_before>transitions.Status_final_after)

transitions.loc[no_changes, 'Status_change'] = 'unverändert'
transitions.loc[forward, 'Status_change'] = 'neu'
transitions.loc[backward, 'Status_change'] = 'zurückgestuft'

changes = ['neu', 'unverändert', 'zurückgestuft']
changes_cat = CategoricalDtype(categories=changes,
                               ordered=True)
transitions['Status_change'] = transitions['Status_change'].astype(changes_cat)

colors = {'neu':'rgb(0, 128, 64)', #green
          'unverändert':'rgb(255, 153, 0)', #orange
          'zurückgestuft':'rgb(204, 0, 0)' #red
         }

data = []


for stat in transitions.Status_change.cat.categories:
    filtered = transitions[transitions.Status_change==stat]
    grouped = filtered.groupby(['Status_final_after']).count()
    x = grouped.index.tolist()
    y = grouped.Status_change.tolist()
    data.append(go.Bar(x=x, y=y, name=stat, marker = dict(color = colors[stat])))
    
timespan = f'{fourteen_days_ago.strftime("%d.%m.%Y")} bis {pd.datetime.today().strftime("%d.%m.%Y")}'
layout = go.Layout(
    barmode='stack',
    title=f'Statusveränderungen im VW JIRA (Maßnahmen): {timespan}',
    xaxis=go.layout.XAxis(
        title=go.layout.xaxis.Title(
            text='Statuskategorien',
            font=dict(
                family='Courier New, monospace',
                size=18,
                color='#7f7f7f'
            )
        )
    ),
    yaxis=go.layout.YAxis(
        title=go.layout.yaxis.Title(
            text='Anzahl der Maßnahmen',
            font=dict(
                family='Courier New, monospace',
                size=18,
                color='#7f7f7f'
            )
        )
    ),
)

fig = go.Figure(data=data, layout=layout)

plot(fig, filename=f'Statusänderungen_Maßnahmen_{fourteen_days_ago.strftime("%d.%m.%Y")}.html')






