from langchain.vectorstores.faiss import FAISS
from langchain.embeddings import OpenAIEmbeddings
import pickle
import os
import io
import csv
from typing import List
from dotenv import load_dotenv
import openai
from definitions import VECTORSTORE_FOLDER



class Faiss():
    def __init__(self):
        load_dotenv()
        openai.api_key = os.environ.get('OPENAI_API_KEY')

    @staticmethod
    def load_vectorstore(file_name):
        # Check if the pickle file exists in vecotrstore folder
        if os.path.exists(VECTORSTORE_FOLDER + file_name + '.pkl'):
            # Load the vectorstore
            with open(VECTORSTORE_FOLDER + file_name + '.pkl', "rb") as f:
                return pickle.load(f)
        else:
            return None  
        
    @staticmethod      
    def embed_doc(file_name, csv_data):
        contents: List[str] = []
        metadata: List[dict] = [] 

        reader = csv.DictReader(io.StringIO(csv_data))
        for row in reader:
            #print(row['content'])
            content = row['content']
            if content is None:  # replace None with empty string
                content = ''
            
            print(row)
            
            contents.append(content)
            metadata.append(row)

        # Load Data to vectorstore
        embedding = OpenAIEmbeddings()

        # I'm using add_texts to run every row the embeddings and add to the Chroma vectorstore.
        # vectorstore = vectorstore.add_texts(contents, metadata)
        vectorstore = FAISS.from_texts(
        texts=contents, embedding=embedding, metadatas=metadata)

        vector_file_path = VECTORSTORE_FOLDER + file_name + '.pkl'
        # Save vectorstore to a pickle file
        with open(vector_file_path, "wb") as f:
            pickle.dump(vectorstore, f)

