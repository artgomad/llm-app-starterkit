import os
import json
import math
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow
from google.auth.transport.requests import Request
from googleapiclient.discovery import build

# If modifying these SCOPES, delete the file token.json.
SCOPES = ['https://www.googleapis.com/auth/spreadsheets']
# The ID and range of the spreadsheet.
SAMPLE_SPREADSHEET_ID = '1ljoRDB7EAOEzD-agCkVPiJU8-JU6oRRu2sd5UN4M3ic'

# Define a function to convert Excel column number to letter (e.g., 1 -> A, 2 -> B, ...)


def col_num_to_letter(n):
    string = ""
    while n > 0:
        n, remainder = divmod(n - 1, 26)
        string = chr(65 + remainder) + string
    return string


def google_sheets_operations(creds, function_output):

    SHEET_NAME = function_output.get('calculation_sheet', 'User profile')
    TYPE_RANGE_WRITE = f'{SHEET_NAME}!B1:AZ3'
    TYPE_RANGE_READ = f'{SHEET_NAME}!B1:AZ50'

    try:
        # 01 READ GOOGLE SHEETS TO IDENTIFY INPUT AND OUTPUT CELLS

        service = build('sheets', 'v4', credentials=creds)
        sheet = service.spreadsheets()

        result = sheet.values().get(spreadsheetId=SAMPLE_SPREADSHEET_ID,
                                    range=TYPE_RANGE_WRITE).execute()
        original_table = result.get('values', [])

        # 02 IDENTIFY CELLS TO WRITE

        write_data = []

        for column in range(len(original_table[0])):

            column_type = original_table[0][column]  # Row 1 in the column
            attribute_name = original_table[1][column]  # Row 2 in the column
            cell_value = original_table[2][column]  # Row 3 in the column
            cell_coordinates = SHEET_NAME + '!' + \
                col_num_to_letter(column + 2) + '3'
            value_to_write = function_output.get(attribute_name, "")

            # Convert value_to_write (a list defined by GPT) to string
            if isinstance(value_to_write, list):
                value_to_write_str = ','.join(map(str, value_to_write))
            else:
                value_to_write_str = str(value_to_write)

            if column_type == 'write':
                obj = {
                    'type': column_type,
                    'name': attribute_name,
                    'cell_coordinates': cell_coordinates,
                    'new_value': value_to_write_str
                }
                write_data.append(obj)

        print("write_data")
        print(write_data)

        # 03 LOOP THROUGH write_data AND MAKE A BATCH WRITE REQUEST

        data_to_update = [{'range': obj['cell_coordinates'], 'values': [[obj['new_value']]]}
                          for obj in write_data]

        body = {
            'valueInputOption': 'RAW',
            'data': data_to_update
        }

        response = sheet.values().batchUpdate(
            spreadsheetId=SAMPLE_SPREADSHEET_ID, body=body).execute()

        print('Updated cells', response)

        # 04 READ THE UPDATED TABLE

        result = sheet.values().get(spreadsheetId=SAMPLE_SPREADSHEET_ID,
                                    range=TYPE_RANGE_READ).execute()
        updated_table = result.get('values', [])

        # 05 EXTRACT CONTEXT FROM 'read-string' CELLS

        context_output = ""

        for column in range(len(updated_table[0])):
            column_type = updated_table[0][column]  # Row 1 in the column
            cell_value = updated_table[2][column]  # Row 3 in the column

            if column_type == 'read-string':
                if context_output:
                    context_output += "\n\n" + cell_value
                else:
                    context_output = cell_value

        print("context_output")
        print(context_output)

        # 06 EXTRACT SELECTED OBJECTS FROM 'read-object' CELLS

        def is_object_attribute(column_type):
            # Helper function to check if column type starts with 'read-object'
            return str(column_type).startswith('read-object')

        selected_objects = []

        object_attribute_columns = [i for i, col_type in enumerate(
            updated_table[0]) if is_object_attribute(col_type)]

        print("object_attribute_columns")
        print(object_attribute_columns)

        for row_idx in range(2, len(updated_table)):
            obj_row = updated_table[row_idx]
            # Make sure obj_row is the same length as updated_table[1]
            obj_row += [''] * (len(updated_table[1]) - len(obj_row))

            print(f'obj_row: {obj_row}')
            obj = {}
            for col_idx in object_attribute_columns:
                print(f'col_idx: {col_idx}')
                print(f'{updated_table[1][col_idx]}: {obj_row[col_idx]}')
                obj.update({updated_table[1][col_idx]: obj_row[col_idx]})

            print(f'obj: {obj}')
            selected_objects.append(obj)

        print("selected_objects")
        print(selected_objects)

        return selected_objects, context_output

    except Exception as e:
        print(f"An error occurred: {e}")
        # return an empty list and empty string as a fallback
        return [], ""


def google_sheets_calculator(function_output):
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

    objects, value = google_sheets_operations(creds, function_output)
    return objects, value


"""
# LOCAL TESTING
if __name__ == '__main__':
    google_sheets_calculator()
"""

"""
    #Pass this array as a paremeter of the API call from the front end called 'GoogleSHeets_coordinates'
    # Alternatively, this function could be smart enough to understand from google sheets 
      what cells represent inputs, single outputs or range outputs, based on how the columns are labeled 
      in the sheets directly.
      Given the cell structure in Google sheets this function will create a JSON object like the ones below
      and loop over the elements to write and read accordingly depending on its type.

     example_JSON_input=  [
            { 
                'type':'input', #EXTRACTED FROM C1
                'name':'INPUT_CELL_SIX_MONTH_DISCOUNT', #EXTRACTED FROM C2
                'value_cell':'User profile!C3', #EXTRACTED FROM C3
                'value':'Yes', #EXTRACTED FROM function_output.get('six_month_discount',"")
                  
            }
            { 
                'type':'input', #EXTRACTED FROM D1
                'name':'INPUT_CELL_SIX_MONTH_DISCOUNT', #EXTRACTED FROM D2
                'value_cell':'User profile!C3', #EXTRACTED FROM D3
                'value':'Yes', #EXTRACTED FROM function_output.get('six_month_discount',"")
                  
            }
            {
                'value':'User profile!E3:Q50', 
                'key_names':'User profile!E2:Q2', 
                'type':'output-objects-from-range',
                'name':'PRODUCT_INFO_CELL_RANGE',
                from_range: 'E3'
                to_range: 'Q50'
                  
            }
        ]
"""
"""
    # Change this to the cell you want to write to
    INPUT_CELL_SIX_MONTH_DISCOUNT = 'User profile!B3'
    INPUT_CELL_ITEMS = 'User profile!C3'
    OUTPUT_CELL = 'User profile!S3'
    PRODUCT_INFO_CELL_RANGE = 'User profile!E3:Q50'
    PRODUCT_ATTRIBUTES_CELL_RANGE = 'User profile!E2:Q2'

    six_month_discount = function_output.get('six_month_discount', "Yes")
    items = function_output.get('items', [])

    # I SHOULD ONLY GO ON IF ITEMS IS NOY AN EMPTY ARRAY
    if not items:
        return [], ""

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
"""
