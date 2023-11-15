# This Python script provides a GoogleSheetsAuthenticator class that manages OAuth 2.0 authentication
# for Google Sheets API access.
# It uses a MongoDB collection to persistently store and retrieve Google API tokens,
# enabling the application to maintain authenticated sessions across restarts.
# The class automates the process of loading stored credentials,
# refreshing them upon expiration, and initiating a new authentication flow if necessary.
# It is designed to interact seamlessly with the Google Sheets API and a MongoDB database
# configured in the mongo_db_setup module.
import os
import json
from google.oauth2.credentials import Credentials
from google.auth.transport.requests import Request
from google_auth_oauthlib.flow import InstalledAppFlow

# Import the MongoDB client from mongo_db_setup
from .mongo_db_setup import tokens_collection


class Config:
    SCOPES = ['https://www.googleapis.com/auth/spreadsheets']


class GoogleSheetsAuthenticator:
    def __init__(self, scopes):
        self.scopes = scopes
        self.creds = None
        self.load_credentials()

    def load_credentials(self):
        # Load credentials from MongoDB
        token_document = tokens_collection.find_one(
            {"service": "google_sheets"})
        if token_document:
            self.creds = Credentials.from_authorized_user_info(
                token_document['token_info'])

    def refresh_credentials(self):
        # Refresh the credentials if expired and save the new token to MongoDB
        if self.creds and self.creds.expired and self.creds.refresh_token:
            self.creds.refresh(Request())
            tokens_collection.update_one(
                {"service": "google_sheets"},
                {"$set": {"token_info": json.loads(self.creds.to_json())}},
                upsert=True
            )
        else:
            # Load client secrets from an environment variable
            client_secrets_json = json.loads(
                os.environ['GOOGLE_CLIENT_SECRET'])
            # Perform the OAuth flow to obtain new credentials
            flow = InstalledAppFlow.from_client_config(
                client_secrets_json, self.scopes)
            self.creds = flow.run_local_server()  # port=0
            # Save the new credentials to MongoDB
            tokens_collection.insert_one({
                "service": "google_sheets",
                "token_info": json.loads(self.creds.to_json())
            })

    def get_credentials(self):
        # If credentials are not valid, refresh or obtain new ones
        if not self.creds or not self.creds.valid:
            self.refresh_credentials()
        return self.creds
