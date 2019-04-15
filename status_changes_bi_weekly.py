import pandas as pd
from pandas.tseries.offsets import Day
from pandas.api.types import CategoricalDtype
from jira.client import JIRA


from format_df import JiraDf
from cocoa import Connection

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
        'author',
        'date',
        'from',
        'to'
       ]

new_cols = ['Key',
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
            'Author', 
            'Date',
            'From',
            'To',
           ]

def getForwardChanges():
    forward_changes_lastweek = '''project = DC AND 
                                  labels in (VW-PKW, 
                                             VW-PKW_InKlaerungKILX
                                             ) AND 
                                  status in ("Concept legally approved", 
                                             "Technical Implementation Started", 
                                             Resolved, 
                                             Closed
                                             ) AND 
                                  updated >= -15d'''
    fw_issues = jira.search_issues(jql_str=forward_changes_lastweek, 
                                   maxResults=False, expand='changelog')
    fw_df = JiraDf(issues=fw_issues,
                   jira_client=jira, 
                   frontendcolname=True, 
                   stringvalues=True, 
                   changelog=True).df
                   
    fw_df.dropna(axis=1, how='all', inplace=True)

    fw_df = fw_df.reindex(columns=cols)
    
    fw_df['date'] = pd.to_datetime(fw_df['date'], dayfirst=True)
    
    fw_df = fw_df[(fw_df['date'] >= pd.datetime.today() - Day(14)) & (fw_df['Status'] == fw_df['to'])]
    
    fw_df.sort_values('date', ascending=True, inplace=True)
    
    fw_df.drop_duplicates(subset=['key', 'to'], keep='first', inplace=True)
        
    fw_df.columns = new_cols
    
    fw_df.sort_values('Date', ascending=False, inplace=True)
    
    fw_df['Date'] = fw_df['Date'].map(lambda x: x.strftime('%d.%m.%Y'))
    
    fw_df['Key'] = fw_df['Key'].map(lambda x: f'=HYPERLINK("https://cocoa.volkswagen.de/sjira/browse/{x}", "{x}")')
    
    return fw_df


def getBackwardChanges():
    
    backward_changes_lastweek = '''project = DC AND
                                   labels in (VW-PKW, VW-PKW_InKlaerungKILX) AND
                                   status in ("Design Decision",
                                              "Concept Decision",
                                              "Order approval",
                                              Draft) AND
                                   updated >= -15d'''
    bw_issues = jira.search_issues(jql_str=backward_changes_lastweek, maxResults=False, expand='changelog')
    
    bw_df = JiraDf(bw_issues, jira_client=jira, frontendcolname=True, stringvalues=True, changelog=True).df

    bw_df.dropna(axis=1, how='all', inplace=True)
    
    bw_df = bw_df.reindex(columns=cols)
    
    bw_df['date'] = pd.to_datetime(bw_df['date'], dayfirst=True)
    
    sorter = ['Created',
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
    
    cat_type = CategoricalDtype(categories=sorter,
                                ordered=True)
    
    bw_df['to'] = bw_df['to'].astype(cat_type)
    bw_df['from'] = bw_df['from'].astype(cat_type)
    
    bw_df = bw_df[(bw_df['date'] >= pd.datetime.today() - Day(14)) & (bw_df['from']>=bw_df['to'])].sort_values(['key','date'])
    
    bw_df.drop_duplicates(subset=['key'], keep='first', inplace=True)
    
    bw_df['to'] = bw_df['Status']
    
    bw_df.columns = new_cols
    
    bw_df.sort_values('Date', ascending=False, inplace=True)
    
    bw_df['Date'] = bw_df['Date'].map(lambda x: x.strftime('%d.%m.%Y'))
    
    bw_df['Key'] = bw_df['Key'].map(lambda x: f'=HYPERLINK("https://cocoa.volkswagen.de/sjira/browse/{x}", "{x}")')
    
    return bw_df

try:
    jira = Connection(stored_cookie=True, 
                      async_=False, 
                      async_workers=None).jira
    if not isinstance(jira, JIRA):
        raise ValueError
except (ValueError, FileNotFoundError):
    jira = Connection().jira

fw_df = getForwardChanges()
bw_df = getBackwardChanges()

current_date = pd.datetime.today().strftime('%d.%m.%Y')

writer = pd.ExcelWriter(f'Report_status_changes_14_days_{current_date}.xlsx')
fw_df.to_excel(writer, sheet_name='Bearbeitete Maßnahmen', index=False)
bw_df.to_excel(writer, sheet_name='Zurückgestufte Maßnahmen', index=False)
writer.save()