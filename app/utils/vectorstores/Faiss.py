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
    def __init__(self, file_name: str):
        load_dotenv()
        openai.api_key = os.environ.get('OPENAI_API_KEY')

        self.file_name = file_name
        self.vectorstore = VECTORSTORE_FOLDER + file_name + '.pkl'

    def load_vectorstore(self):
        # Check if the pickle file exists in vecotrstore folder and load it
        if os.path.exists(self.vectorstore):
            with open(self.vectorstore, "rb") as f:
                return pickle.load(f)
        else:
            return None  
            
    def embed_doc(self, csv_data):
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

        vectorstore = FAISS.from_texts(
        texts=contents, embedding=embedding, metadatas=metadata)

        # Save vectorstore to a pickle file
        with open(self.vectorstore, "wb") as f:
            print("SAVING VECTORSTORE TO PICKLE FILE")
            pickle.dump(vectorstore, f)

    def vector_search(self, query: str, number_of_outputs:int) -> str:
        # Check if the pickle file exists in vecotrstore folder and load it
        if os.path.exists(self.vectorstore):
            with open(self.vectorstore, "rb") as f:
                vectorstore = pickle.load(f)
                print("loading vectorstore...")
        else:
            print("vectorstore not found")

        print('User question: ' + query)

        # Get the top X documents from the vectorstore
        docs_and_scores = vectorstore.similarity_search_with_score(query, number_of_outputs)
        #docs = vectorstore.similarity_search(query, number_of_outputs)

        docs_content = ""
        docs_result = []
        for doc, score in docs_and_scores:
            
            docs_content += doc.metadata['content']
            doc.metadata['score'] = float(score)

            doc_dict = {
            'metadata': doc.metadata,
            'content': docs_content
            }
            print(doc_dict)
            docs_result.append(doc_dict)

        return docs_result, docs_content

