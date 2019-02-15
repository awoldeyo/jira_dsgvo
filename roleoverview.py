import jira.client
from jira.client import JIRA
from pycookiecheat import chrome_cookies
import pandas as pd

# Authentifizierung VW Cocoa; Bitte vorher über Chrome Browser einloggen.
url = 'https://cocoa.volkswagen.de/sjira/'
cookies = chrome_cookies(url)

# JIRA Authentifizierung
jira_options={'server': url, 'cookies':cookies}
jira=JIRA(options=jira_options)

# JIRA Projekt-IDs + Projektbezeichnung
project_ids = {'12302':'DC', '11605':'DAML'}

# Verfügbare Rollen je Projekt-ID abfragen und in Dictionary (key=Projekt-ID & value=Projektrolle) speichern
project_roles = {k:jira.project_roles(k) for k,v in project_ids.items()}

# Abfrage der einer Projektrolle zugeordneten JIRA-User (Projekt, Rolle + ID, VW_User_ID, Name, Group)
collect = []
for project,roles in project_roles.items():
    for role,data in roles.items():
        group = jira.project_role(project=project, id=data['id'])
        collect += [[project, role, a.id, a.name, a.displayName, a.type] for a in group.actors]

# Aus den gesammelten Daten ein DataFrame erstellen
df = pd.DataFrame(collect, columns=['Project', 'Role', 'ID', 'VW_User_ID', 'Name', 'Group'])

# Die Spalte Projekt-ID mappen (Projekt-ID -> Projektbezeichnung)
df.Project = df.Project.map(lambda x: project_ids.get(x,None))

# Alternative A: Für jedes Projekt eine Excel-Datei (writer), für jede Rolle ein Tabellenblatt (sheet_name) erzeugen
for project in df.Project.unique():
    writer = pd.ExcelWriter(f'{project}_user_roles.xlsx', engine='xlsxwriter')
    for role in df[df.Project == project].Role.unique():
        df[(df.Project==project) & (df.Role==role)].to_excel(writer, sheet_name=role, index=False)
writer.save()

# Alternative B: Eine Excel-Datei (writer) für alle Projekte und Rollen erzeugen

writer = pd.ExcelWriter('user_roles.xlsx', engine='xlsxwriter')

for project in df.Project.unique():
    df[df.Project==project].to_excel(writer, sheet_name=project, index=False)
writer.save()
