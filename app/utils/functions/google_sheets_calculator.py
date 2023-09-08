import os
import json
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow
from google.auth.transport.requests import Request
from googleapiclient.discovery import build

# If modifying these SCOPES, delete the file token.json.
SCOPES = ['https://www.googleapis.com/auth/spreadsheets']

# The ID and range of the spreadsheet.
SAMPLE_SPREADSHEET_ID = '1ljoRDB7EAOEzD-agCkVPiJU8-JU6oRRu2sd5UN4M3ic'
# Change this to the cell you want to write to
INPUT_CELL = 'User profile!B3'
OUTPUT_CELL = 'User profile!S4'
PRODUCT_INFO_CELL_RANGE = 'User profile!E4:Q50'
PRODUCT_ATTRIBUTES_CELL_RANGE = 'User profile!E3:Q3'


def google_sheets_operations(creds):
    # Call the Sheets API
    service = build('sheets', 'v4', credentials=creds)
    sheet = service.spreadsheets()

    # Write to the input cell
    request = sheet.values().update(spreadsheetId=SAMPLE_SPREADSHEET_ID, range=INPUT_CELL,
                                    valueInputOption='RAW', body={'values': [['Testing it works!']]})
    response = request.execute()

    print(response)

    print('Updated cell', response)

    # Read the value of output cell
    result = sheet.values().get(spreadsheetId=SAMPLE_SPREADSHEET_ID,
                                range=OUTPUT_CELL).execute()
    value = result.get('values', [])[0][0]

    print('Extracted cell value', value)

    # Read the values of selected products
    result = sheet.values().get(spreadsheetId=SAMPLE_SPREADSHEET_ID,
                                range=PRODUCT_INFO_CELL_RANGE).execute()
    values = result.get('values', [])

    # Read the column names for the product attributes
    result = sheet.values().get(spreadsheetId=SAMPLE_SPREADSHEET_ID,
                                range=PRODUCT_ATTRIBUTES_CELL_RANGE).execute()
    column_names = result.get('values', [])[0]

    # Convert the values to an array of objects
    objects = []
    for row in values:
        obj = {}
        for i in range(len(column_names)):
            if i < len(row):
                obj[column_names[i]] = row[i]
        objects.append(obj)

    print('Extracted objects:', objects)

    return objects, value


def google_sheets_calculator():
    # CONNECTING WITH GOOGLE SHEETS API

    creds = None

    """
    # LOCAL TESTING
    # The file token.json stores the user's access and refresh tokens, and is
    # created automatically when the authorization flow completes for the first time.
    if os.path.exists('token.json'):
        creds = Credentials.from_authorized_user_file('token.json')
    """

    # USING HEROKU CONFIG VARS
    # Use the tokens saved in the GOOGLE_SHEETS_TOKENS config var
    GOOGLE_SHEETS_TOKENS = os.environ['GOOGLE_SHEETS_TOKENS']
    if GOOGLE_SHEETS_TOKENS:
        creds = Credentials.from_authorized_user_info(
            json.loads(GOOGLE_SHEETS_TOKENS))

    # If there are no (valid) credentials available, prompt the user to log in.
    if not creds or not creds.valid:
        if creds and creds.expired and creds.refresh_token:
            creds.refresh(Request())
        else:
            """
            # LOCAL TESTING
            flow = InstalledAppFlow.from_client_secrets_file(
                'client_secret.json', SCOPES)
            """
            # USING HEROKU CONFIG VARS
            client_secret_json = json.loads(os.environ['GOOGLE_CLIENT_SECRET'])
            flow = InstalledAppFlow.from_client_info(
                client_secret_json, SCOPES)
            creds = flow.run_local_server(port=5000)

        # Save the credentials for the next run
        with open('token.json', 'w') as token:
            token.write(creds.to_json())

    objects, value = google_sheets_operations(creds)
    return objects, value


"""
# LOCAL TESTING
if __name__ == '__main__':
    google_sheets_calculator()
"""
