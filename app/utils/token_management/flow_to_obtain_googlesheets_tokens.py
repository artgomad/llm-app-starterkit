# This code is a Python script for obtaining OAuth 2.0 credentials and tokens
# from a user to access the Google Sheets API.
# By running this script, a user grants the application permission
# to access and manage their Google Sheets through the API.
# The credentials are saved locally in client_secret.json and token.json
# Which can be uploaded to Heroku Config Vars manually (GOOGLE_CLIENT_SECRET and GOOGLE_SHEETS_TOKENS)
# to enable the app to access the Google Sheets API.

import os
from google_auth_oauthlib.flow import InstalledAppFlow

# Scopes define the level of access you are requesting from the user.
SCOPES = ['https://www.googleapis.com/auth/spreadsheets']


def main():
    flow = InstalledAppFlow.from_client_secrets_file(
        'client_secret.json', SCOPES)
    # This will run a local web server.
    creds = flow.run_local_server(port=5000, prompt='consent')

    # Save the credentials for the next run
    with open('token.json', 'w') as token:
        token.write(creds.to_json())

    print('New tokens acquired and saved.')


if __name__ == '__main__':
    main()
