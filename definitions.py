import os

ROOT_DIR = os.path.dirname(os.path.abspath(__file__))
PROJECT_ROOT = os.path.dirname(ROOT_DIR)

DATA_PATH = os.path.join(PROJECT_ROOT, 'data')

CSV_FOLDER = os.path.join(DATA_PATH, 'csv_files/')
VECTORSTORE_FOLDER = os.path.join(
    DATA_PATH, 'vectorstores/')  # 'data/vectorstores/'

# Create the folders if they don't exist
os.makedirs(CSV_FOLDER, exist_ok=True)
os.makedirs(VECTORSTORE_FOLDER, exist_ok=True)
