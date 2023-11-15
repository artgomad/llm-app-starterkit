import os
from google_auth_oauthlib.flow import InstalledAppFlow

# Scopes define the level of access you are requesting from the user.
SCOPES = ['https://www.googleapis.com/auth/spreadsheets']


def main():
    flow = InstalledAppFlow.from_client_secrets_file(
        'client_secret.json', SCOPES)
    # This will run a local web server.
    creds = flow.run_local_server(port=5000)

    # Save the credentials for the next run
    with open('token.json', 'w') as token:
        token.write(creds.to_json())

    print('New tokens acquired and saved.')


if __name__ == '__main__':
    main()
