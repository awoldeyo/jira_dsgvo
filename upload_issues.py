from optparse import OptionParser

import pandas as pd
from pandas import ExcelWriter
from jira.exceptions import JIRAError
from openpyxl import load_workbook

from cocoa import Connection
from upload_resources import excelname_mapping, dc_cols, daml_cols, dtype, heatmap, heatmap_area, template_cols


class UploadIssues(object):
    '''Upload issues (DAML & DC) from Excel upload document.
       
       Parameters
       ----------
       filename : path to Excel upload document
    '''

    def __init__(self, filename):
        self.daml_blueprint = pd.read_pickle('./project_blueprints/daml_blueprint.pickle')
        self.dc_blueprint = pd.read_pickle('./project_blueprints/dc_blueprint.pickle')
        self.mandatory_DAML_cols = [c for c in daml_cols if "*" in c]
        self.mandatory_DC_cols = [c for c in dc_cols if "*" in c]
        self.filename = filename
        self.df = pd.read_excel(self.filename, skiprows=1, dtype=dtype)
        self.prepareFile()
    
    def prepareFile(self):
        # Format date to string
        self.df['Due-Date implemented'] = self.df['Due-Date implemented'].map(
                lambda x: x.strftime('%Y-%m-%d') if pd.notna(x) else ''
                )
        
        # Fill N/A with empty string for optional columns
        optional_cols = ['Sub Department', 
                         'Contact person (business department)', 
                         'Contact person (IT)', 
                         'Market'
                         ]
        self.df.loc[:, optional_cols].fillna('', inplace=True)
        
        # Cleanup data (remove trailing whitespace ...)
        self.df = self.df.applymap(lambda x: x.strip() if isinstance(x, str) else x)
        
        # Create Heat-Map and Areas of activity Heatmap columns
        self.df['Heat-Map'] = self.df['Detailed Type*'].map(
                lambda x: heatmap.get(x, None)
                )
        self.df['Heat-Map'] = self.df['Heat-Map'].map(
                lambda x: f'{int(x)}' if pd.notna(x) else None
                )
        self.df['Areas of activity Heatmap'] = self.df['Detailed Type*'].map(
                lambda x: heatmap_area.get(x, None)
                )
        
        self.df['Linked Issue DC'] = None

        
    def createUploadDictDAML(self):
        # Determine which DAML rows are valid 
        # (i.e. all mandatory columns are filled out)
        self.valid_DAML_rows = self.df.dropna(
                axis='index', 
                subset=self.mandatory_DAML_cols
                ).index
        
        # Determine DAML that can be uploaded and create dictionary for upload 
        condition_1 = (self.df.index.isin(self.valid_DAML_rows)) # 1. Mandatory columns are all filled
        condition_2 = (self.df['Linked Issue'].isna()) # 2. Issues have not been linked yet
        daml_filter = condition_1 & condition_2
        
        # Create upload dictionary
        self.df.loc[daml_filter, 'DAML dict'] = self.df[daml_filter].reindex(
                daml_cols, 
                axis=1).fillna('').apply(
                        lambda x: df_to_issuedict(x, self.daml_blueprint, 'DAML'), 
                        axis=1)
        
        # Determine incomplete rows
        incomplete_rows = self.df.loc[daml_filter==False].index
        
        # Create dataframe from incomplete row(s)
        self.incomplete_df = self.df.loc[incomplete_rows, :]
        
        # Drop incomplete row(s) from original dataframe
        self.df.drop(labels=incomplete_rows, axis=0, inplace=True)
        
        # Store incorrect dataframe in new Upload template
        book = load_workbook('template/UpoadFile2_version_1.3.xlsm')
        writer = ExcelWriter('output/Incomplete_data.xlsx', engine='openpyxl')
        writer.book = book
        writer.sheets = dict((ws.title, ws) for ws in book.worksheets)
        self.incomplete_df.to_excel(
                excel_writer=writer,
                sheet_name='Upload',
                header=False,
                index=False,
                startrow=2
                )
        writer.save()

    def createUploadDictDC(self):         
         # Determine which DC rows are valid 
         # (i.e. all mandatory columns are filled out)
         self.valid_DC_rows = self.df.dropna(
                 axis='index', 
                 subset=self.mandatory_DC_cols
                 ).index
                 
         # Determine DC that can be uploaded and create dictionary for upload 
         condition_1 = (self.df.index.isin(self.valid_DC_rows)) # 1. Mandatory columns are all filled
         condition_2 = (self.df['Linked Issue DC'].isna()) # 2. Issues have not been linked yet
         dc_filter = condition_1 & condition_2
         
         # Create upload dictionary
         self.df.loc[dc_filter, 'DC dict'] = self.df[dc_filter].reindex(
                 dc_cols, 
                 axis=1).fillna('').apply(
                         lambda x: df_to_issuedict(x, self.dc_blueprint, 'DC'), 
                         axis=1)
         
         # Determine incomplete rows
         condition_3 = self.df['Linked Issue'].notna() # Linked Issue, i.e. corresponding DAML issue exists
         condition_4 = (dc_filter == False) # Not in dc_filter (i.e. mandatory field not filled and not linked yet)
         incomplete_rows = self.df.loc[condition_3 & condition_4].index
         
         # Add incomplete row(s) to existing incomplete dataframe
         self.incomplete_df = pd.concat(
                 (self.incomplete_df, self.df.loc[incomplete_rows, :]), 
                 sort=True
                 )
         
         # Drop incomplete row(s) from original dataframe
         self.df.drop(labels=incomplete_rows, axis=0, inplace=True)
         
          # Reindex incomplete dataframe columns to match original template
         self.incomplete_df = self.incomplete_df.reindex(
                 labels=template_cols,
                 axis=1
                 )
         
         book = load_workbook('template/UpoadFile2_version_1.3.xlsm')
         writer = ExcelWriter('output/Incomplete_data.xlsx', engine='openpyxl')
         writer.book = book
         writer.sheets = dict((ws.title, ws) for ws in book.worksheets)
         self.incomplete_df.to_excel(
                 excel_writer=writer,
                 sheet_name='Upload',
                 header=False,
                 index=False,
                 startrow=2
                 )
         writer.save()


    def postDAML(self):
        
# =============================================================================
#         # Create new columns for successfull upload (boolean) and error messges
#         self.df['DAML_upload_success'] = False
#         self.df['DAML_Error_message'] = None
#         
#         # Define column arguments for processing upload
#         col_args = ('DAML dict',
#                     'DAML_Error_message', 
#                     'Linked Issue', 
#                     'DAML_upload_success', 
#                     )
#         
#         # Post DAML issues
#         self.df = self.df.apply(post_issues, args=col_args, axis=1)
# =============================================================================
        
        self.df['results'] = self.df['DAML dict'].map(post_issues)
        results = self.df.apply(lambda x: x['results'], 
                                axis=1, 
                                result_type='expand').copy()
        results.columns = ['Linked Issue', 
                           'DAML_upload_success', 
                           'DAML_Error_message'
                           ]
        self.df.drop(labels=['Linked Issue'], 
                     axis=1, 
                     inplace=True)
        self.df = pd.concat((self.df, results), 
                            axis=1).drop(
                                    labels=['results'], axis=1
                                    )
        
        # Create incorrect dataframe for not successfully uploaded DAML issues
        self.incorrect_df = self.df.loc[self.df.DAML_upload_success==False,:].copy(True)
        
        # Drop incorrect rows from original dataframe
        self.df.drop(
                labels=self.incorrect_df.index, 
                axis=0, 
                inplace=True)
        
        # Drop irrelevant columns from incorrect dataframe
        self.incorrect_df.drop(labels=['Heat-Map',
                                       'Linked Issue DC',
                                       'Areas of activity Heatmap',
                                       'DAML dict',
                                       'DAML_upload_success',
                                       ], 
                                axis=1, 
                                inplace=True
                                )
        
        # Store incorrect dataframe in new Upload template
        book = load_workbook('template/UpoadFile2_version_1.3.xlsm')
        writer = ExcelWriter('output/Incorrect_data.xlsx', engine='openpyxl')
        writer.book = book
        writer.sheets = dict((ws.title, ws) for ws in book.worksheets)
        self.incorrect_df.to_excel(
                excel_writer=writer,
                sheet_name='Upload',
                header=False,
                index=False,
                startrow=2
                )
        writer.save()
    
    def postDC(self):
        
# =============================================================================
#         # Create new columns for successfull upload (boolean), error messges
#         # and DC issue Link
#         self.df['DC_upload_success'] = False
#         self.df['DC_Error_message'] = None
#         self.df['Linked Issue DC'] = None
#         
#         # Define column arguments for processing upload
#         col_args = ('DC dict',
#                     'DC_Error_message', 
#                     'Linked Issue DC', 
#                     'DC_upload_success',
#                     )
#         
#         # Post DC issues
#         self.df = self.df.apply(post_issues, args=col_args, axis=1)
# =============================================================================
        
        self.df['results'] = self.df['DC dict'].map(post_issues)
        results = self.df.apply(lambda x: x['results'], 
                                axis=1, 
                                result_type='expand').copy()
        results.columns = ['Linked Issue DC', 
                           'DC_upload_success', 
                           'DC_Error_message'
                           ]
        
        self.df.drop(labels=['Linked Issue DC'], 
                     axis=1, 
                     inplace=True)
        
        self.df = pd.concat((self.df, results), 
                            axis=1).drop(
                                    labels=['results'], axis=1
                                    )
        
        # Add not successfully uploaded DC issues to incorrect dataframe
        self.incorrect_df_DC = self.df.loc[self.df.DC_upload_success==False,:]
        if self.incorrect_df_DC.shape[0] >=1:
            self.incorrect_df = pd.concat(
                    (self.incorrect_df, self.incorrect_df_DC),
                    sort=True,
                    )
        
            # Drop incorrect rows from original dataframe
            self.df.drop(
                    labels=self.incorrect_df_DC.index, 
                    axis=0, 
                    inplace=True)
            
            self.incorrect_df.drop(labels=['Heat-Map',
                                           'Areas of activity Heatmap',
                                           'DC dict',
                                           'DC_upload_success',
                                           ], 
                                    axis=1, 
                                    inplace=True
                                    )
        
        # Adjust incorrect dataframe column to template column
        incorrect_cols = template_cols
        self.incorrect_df = self.incorrect_df.reindex(labels=incorrect_cols,
                                                      axis=1,
                                                      )
        
        # Store incorrect dataframe in new Upload template
        book = load_workbook('template/UpoadFile2_version_1.3.xlsm')
        writer = ExcelWriter('output/Incorrect_data.xlsx', engine='openpyxl')
        writer.book = book
        writer.sheets = dict((ws.title, ws) for ws in book.worksheets)
        self.incorrect_df.to_excel(
                excel_writer=writer,
                sheet_name='Upload',
                header=False,
                index=False,
                startrow=2
                )
        writer.save()
              

def from_blueprint(blueprint, field, fieldvalue):
    '''Looks up and returns required data format'''
    index = excelname_mapping.get(field, None)
    fieldtype = blueprint.loc[index,'schema']
    attribute_type = blueprint.loc[index,'attribute_type']
    
    if fieldtype == 'array':
        if pd.notna(attribute_type):
            return [{f'{attribute_type}': fieldvalue}]
        else:
            return fieldvalue.split(',')
    elif fieldtype in ['priority', 'option', 'issuetype']:
        return {f'{attribute_type}': fieldvalue}
    elif fieldtype in ['string', 'date']:
        return fieldvalue
    elif fieldtype == 'user':
        return {'name': fieldvalue}

def df_to_issuedict(item, blueprint, project):
    '''Returns issue dictionaries'''
    issue_dict = {excelname_mapping[c]:from_blueprint(blueprint=blueprint, field=c, fieldvalue=item[c]) for c in item.index}
    if project == 'DAML':
        issue_dict['project'] = {'id': '11605'}
        issue_dict['issuetype'] = {'name': 'Defect'}
        #issue_dict['labels'] = ['VW-PKW'] # uncomment after deployment
        issue_dict['labels'] = ['Testing'] # comment out after deployment
    elif project == 'DC':
        issue_dict['project'] = {'id': '12302'}
        issue_dict['issuetype'] = {'name': 'Task'}
    return issue_dict

def post_issues(x):
    '''Posts Jira issues and returns True/False and Object Key/Error text'''
    try:
        obj = jira.create_issue(x)
        obj_success, obj_key, obj_error= True, obj.key, None
    except JIRAError as j:
        obj_success, obj_key, obj_error = False, None, j.text
    finally:
        return obj_key, obj_success, obj_error
# =============================================================================
#     try:
#         obj = jira.create_issue(x[dict_col])
#         x[link] = obj.key
#         x[success] = True
#     except JIRAError as j:
#         x[error_message] = j.text
#     finally:
#         return x
# =============================================================================


jira = Connection(True).jira
#filename = '/Users/lilitkhurshudyan/Documents/12_Projects/VW/JIRA/__uploads__/test_upload/test.xlsm'
filename = '/Users/lilitkhurshudyan/Documents/12_Projects/VW/JIRA/__uploads__/test_upload/test_2.xlsm'
up = UploadIssues(filename)
up.createUploadDictDAML()
up.postDAML()
up.createUploadDictDC()
up.postDC()

# =============================================================================
# parser = OptionParser()
# args = parser.add_option("-c", action="store_true", dest="stored", help="Use stored cookie to authenticate.")
# (options, args) = parser.parse_args()
# jira = Connection(stored_cookie=options.stored).jira
# =============================================================================
