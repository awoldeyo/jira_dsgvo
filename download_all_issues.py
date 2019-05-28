import pytz

import pandas as pd
from pandas.tseries.offsets import Day
from pandas.api.types import CategoricalDtype

from cocoa import Connection
from format_df import JiraDf

# Create timezone variable (UTC)
tz = pytz.UTC

# Connect to JIRA
jira = Connection().jira

# Collect DC issues
dc_issues = jira.search_issues(
        jql_str='''project = DC AND 
                   labels in (VW-PKW, VW-PKW_InKlaerungKILX)''', 
                   maxResults=False,
                   expand='changelog')

# Create DC issues dataframe
dfDC = JiraDf(issues=dc_issues, 
              jira_client=jira, 
              frontendcolname=True, 
              stringvalues=True, 
              changelog=True).df

# Drop empty columns from dataframe              
dfDC = dfDC.dropna(axis=1, how='all')

# Create new changelog entries for NaN -> "Draft"
draft = dfDC.drop_duplicates(subset='key').copy(True)
draft.loc[:, 'from'] = pd.np.nan
draft.loc[:, 'to'] = 'Draft'
draft.loc[:, 'date'] = draft.loc[:, 'Created']
dfDC = pd.concat((dfDC, draft), axis=0, ignore_index=True)

# Drop duplicated columns from dataframe
dfDC = dfDC.loc[:, dfDC.columns.duplicated()==False]

# Define status categories
status = [
          'Draft',
          'Order approval',
          'Concept Decision',
          'Design Decision',
          'Implemented',
          'Concept legally approved',
          'Technical Implementation Started',
          'Resolved',
          'Closed'
         ]

# Filter for columns "from"/"to" which contain status categories
status_filter = ((dfDC['from'].isin(status)) | (dfDC['to'].isin(status)))

# Apply status filter to dataframe
dfDC = dfDC.loc[status_filter, :]

# Define important columns for final report
important_cols = [
    'key',
    'Department',
    'Component/s',
    'Status',
    'Created',
    'date',
    'from',
    'to',
    ]

# Keep important columns
dfDC = dfDC.reindex(columns=important_cols)

# Create a categorical dtype object based on status category
cat_type = CategoricalDtype(categories=status,
                            ordered=True)

# Change columns "Status"/"to" to categorical dtypes
dfDC.loc[:, 'Status'] = dfDC['Status'].astype(cat_type)
dfDC.loc[:, 'from'] = dfDC['from'].astype(cat_type)
dfDC.loc[:, 'to'] = dfDC['to'].astype(cat_type)


# Apply date formatting to "Created"/"date" columns
dfDC['Created'] = pd.to_datetime(dfDC['Created'])
dfDC['date'] = pd.to_datetime(dfDC['date'])
dfDC['Created'] = dfDC['Created'].dt.tz_localize(tz)
dfDC['date'] = dfDC['date'].dt.tz_localize(tz)

# Sort dataframe by key, date and from
dfDC = dfDC.sort_values(['key', 'date', 'from'], ascending=False)

# Create Timestamp for -14 days ago
fourteen_days_ago = pd.datetime.now(tz) - Day(14)

# Create time filter
date_range = (dfDC['date']<=fourteen_days_ago)

# Create filtered dataframe
dfDC_date_filtered = dfDC.loc[date_range,:].copy(True)

# Store newly created (within 14 days) issues
dfDC_new = dfDC.loc[(dfDC['Created']>=fourteen_days_ago), :].copy(True)

# Transform date column values to string values
dfDC_date_filtered.loc[:, 'date'] = dfDC_date_filtered['date'].map(
        lambda x: x.strftime('%d.%m.%Y')
        )
dfDC_new.loc[:, 'date'] = dfDC_new['date'].map(
        lambda x: x.strftime('%d.%m.%Y')
        )

# Keep latest change per date and key
dfDC_date_filtered = dfDC_date_filtered.drop_duplicates(
        subset=['key']
        )
dfDC_new = dfDC_new.drop_duplicates(
        subset=['key']
        )

dfDC_new.loc[:, 'Status change'] = 'neu'

# Create filter for status change (i.e. compare current status with past status)
no_changes = (dfDC_date_filtered['Status'] == dfDC_date_filtered['to'])
forward = (dfDC_date_filtered['Status'] > dfDC_date_filtered['to'])
backward = (dfDC_date_filtered['Status'] < dfDC_date_filtered['to'])

# Filter and set value in new column Status_change
dfDC_date_filtered.loc[no_changes, 'Status change'] = 'unverändert'
dfDC_date_filtered.loc[forward, 'Status change'] = 'vorgestuft'
dfDC_date_filtered.loc[backward, 'Status change'] = 'zurückgestuft'


dfDC_total = pd.concat((dfDC_date_filtered, dfDC_new), axis=0, sort=False)


dfFinal = dfDC_total.reindex(columns=['key', 'Department', 'Component/s', 'Status', 'Status change'])

status_mapping = {
    "Order approval": "2. Order approval",
    "Resolved": "8. Resolved",
    "Implemented": "5. Implemented",
    "Draft": "1. Draft",
    "Closed": "9. Closed",
    "Concept Decision": "3. Concept Decision",
    "Design Decision": "4. Design Decision",
    "Concept legally approved": "6. Concept legally approved",
    "Technical Implementation Started": "7. Technical Implementation Started",
}

dfFinal['Status'] = dfFinal.Status.map(status_mapping)

# Export final dataframe to excel
dfFinal.to_excel('All_issues_report.xlsx', sheet_name='Report', index=False)