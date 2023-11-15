# This script is used to connect to a MongoDB Atlas cluster using the PyMongo driver.
# The purpose of this script is to establish a connection to the MongoDB database
# and provide a reference to a specific collection within that database.

from pymongo import MongoClient
import os

MONGODB_URI = os.getenv('MONGODB_URI')

client = MongoClient(MONGODB_URI)
db = client['GoogleSheetsTokens_db']
tokens_collection = db['tokenList']
