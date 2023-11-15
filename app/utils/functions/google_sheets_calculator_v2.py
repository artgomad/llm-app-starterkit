import os
import json
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow
from google.auth.transport.requests import Request
from googleapiclient.discovery import build
from typing import Any, Dict, Tuple, Optional
from app.utils.token_management.google_sheets_authenticator import GoogleSheetsAuthenticator, Config

''' 
# I NEED TO DELETE THIS CLASS BECAUSE IT COMES FROM THE GOOGLE_SHEETS_AUTHENTICATOR.PY FILE

class Config:
    SCOPES = ['https://www.googleapis.com/auth/spreadsheets']

# Authentication handler
# I NEED TO DELETE THIS CLASS BECAUSE IT COMES FROM THE GOOGLE_SHEETS_AUTHENTICATOR.PY FILE


class GoogleSheetsAuthenticator:
    def __init__(self, config: Config):
        self.config = config
        self.creds = None
        self.load_credentials()

    def load_credentials(self):
        # Load credentials from environment variables or local file
        tokens = os.environ.get('GOOGLE_SHEETS_TOKENS', None)
        if tokens:
            self.creds = Credentials.from_authorized_user_info(
                json.loads(tokens))
        else:
            if os.path.exists('token.json'):
                self.creds = Credentials.from_authorized_user_file(
                    'token.json')

    def refresh_credentials(self):
        if self.creds and self.creds.expired and self.creds.refresh_token:
            self.creds.refresh(Request())
        else:
            client_secret_json = json.loads(os.environ['GOOGLE_CLIENT_SECRET'])
            flow = InstalledAppFlow.from_client_info(
                client_secret_json, self.config.SCOPES)
            self.creds = flow.run_local_server(port=0)
        self.save_credentials()

    def save_credentials(self):
        with open('token.json', 'w') as token_file:
            token_file.write(self.creds.to_json())
'''

# Google Sheets API communication


class GoogleSheetsAPI:
    def __init__(self, authenticator: GoogleSheetsAuthenticator):
        self.service = build('sheets', 'v4', credentials=authenticator.creds)

    def read_values(self, spreadsheet_id: str, range_name: str):
        result = self.service.spreadsheets().values().get(
            spreadsheetId=spreadsheet_id, range=range_name).execute()
        return result.get('values', [])

    def write_values(self, spreadsheet_id: str, range_name: str, values: list):
        body = {
            'valueInputOption': 'RAW',
            'data': [{'range': range_name, 'values': values}]
        }
        self.service.spreadsheets().values().batchUpdate(
            spreadsheetId=spreadsheet_id, body=body).execute()

    def batch_update_values(self, spreadsheet_id: str, data: list):
        body = {
            'valueInputOption': 'RAW',
            'data': data
        }
        self.service.spreadsheets().values().batchUpdate(
            spreadsheetId=spreadsheet_id, body=body).execute()


def col_num_to_letter(n):
    string = ""
    while n > 0:
        n, remainder = divmod(n - 1, 26)
        string = chr(65 + remainder) + string
    return string

# Main calculator function


def google_sheets_calculator_v2(config: Config, spreadsheet_id: str, sheet_name: str, function_output: dict) -> Tuple[Optional[Dict], str]:
    config = Config()
    authenticator = GoogleSheetsAuthenticator(config.SCOPES)
    if not authenticator.creds or not authenticator.creds.valid:
        authenticator.refresh_credentials()

    sheets_api = GoogleSheetsAPI(authenticator)
    range_read_write = f'{sheet_name}!A1:ZZ'

    try:
        # Read the spreadsheet to determine the input and output cells
        original_table = sheets_api.read_values(
            spreadsheet_id, range_read_write)

        # Initialize an empty list to collect data to write
        write_data = []

        # Assuming the first row is the type, second row is the attribute name, and third row is the value
        if original_table and len(original_table) >= 3:
            for column, column_type in enumerate(original_table[0]):
                if column_type.lower() == 'write':  # Check if the column type is 'write'
                    attribute_name = original_table[1][column]
                    value_to_write = function_output.get(attribute_name, "")
                    cell_coordinates = f'{sheet_name}!{col_num_to_letter(column + 1)}3'

                    # Convert value_to_write (a list defined by GPT) to string
                    if isinstance(value_to_write, list):
                        value_to_write_str = ','.join(map(str, value_to_write))
                    else:
                        value_to_write_str = str(value_to_write)

                    write_data.append({
                        'range': cell_coordinates,
                        'values': [[value_to_write_str]]
                    })

        # Write to the spreadsheet using batchUpdate for efficiency
        if write_data:
            sheets_api.batch_update_values(spreadsheet_id, write_data)

        print(write_data, "Data updated successfully.")

        # Refresh the values after writing
        updated_table = sheets_api.read_values(
            spreadsheet_id, range_read_write)

        # Extract context from 'read-string' cells
        context_output = ""
        selected_objects = []

        if updated_table and len(updated_table) >= 3:
            # Define a helper function to check if column type starts with 'read-object'
            def is_object_attribute(column_type):
                return str(column_type).startswith('read-object')

            # Initialize an empty list to collect objects from 'read-object' cells
            object_attribute_columns = [i for i, col_type in enumerate(
                updated_table[0]) if is_object_attribute(col_type)]

            for row_idx in range(2, len(updated_table)):
                obj_row = updated_table[row_idx]
                # Make sure obj_row is the same length as updated_table[1]
                obj_row += [''] * (len(updated_table[1]) - len(obj_row))

                obj = {}
                for col_idx in object_attribute_columns:
                    attribute = updated_table[1][col_idx]
                    value = obj_row[col_idx]
                    obj[attribute] = value

                selected_objects.append(obj)

            # Extract strings from 'read-string' cells
            for column, column_type in enumerate(updated_table[0]):
                if column_type.lower() == 'read-string':
                    # Assuming the value is in the third row
                    cell_value = updated_table[2][column]
                    context_output += f"{cell_value}\n\n"

        # Clean up the context_output from the last "\n\n"
        context_output = context_output.strip()

        # print("selected_objects")
        # print(selected_objects)

        # Return both the objects extracted and the context information
        return selected_objects, context_output

    except Exception as e:
        return None, f"An error occurred: {str(e)}"


# Example usage
if __name__ == "__main__":
    config = Config()
    spreadsheet_id = '1ljoRDB7EAOEzD-agCkVPiJU8-JU6oRRu2sd5UN4M3ic'
    output = {
        # ... include other parameters as required by the function_output schema ...
        'products_selected': [2, 3],
        'six_month_discount': 'Yes',
    }
    objects, message = google_sheets_calculator_v2(
        config, spreadsheet_id, 'User profile', output)
    print(objects, message)
