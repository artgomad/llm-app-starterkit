import os

ROOT_DIR = os.path.dirname(os.path.abspath(__file__))

DATA_PATH = os.path.join(ROOT_DIR, 'data') 

CSV_FOLDER = os.path.join(DATA_PATH,'csv_files/')
VECTORSTORE_FOLDER = os.path.join(DATA_PATH,'data/vectorstores/')

if not os.path.exists(CSV_FOLDER):
    os.makedirs(CSV_FOLDER)

if not os.path.exists(VECTORSTORE_FOLDER):
    os.makedirs(VECTORSTORE_FOLDER)