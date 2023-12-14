from langchain.vectorstores.faiss import FAISS
from langchain.embeddings import OpenAIEmbeddings
import pickle
import os
import re
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
        self.vectorstore_path = os.path.join(
            VECTORSTORE_FOLDER, file_name + '.bin')

    def load_vectorstore(self):
        # Check if the file exists in vectorstore folder and load it
        if os.path.exists(self.vectorstore_path):
            with open(self.vectorstore_path, "rb") as f:
                serialized_faiss_bytes = f.read()
            embedding = OpenAIEmbeddings()
            return FAISS.deserialize_from_bytes(embeddings=embedding, serialized=serialized_faiss_bytes)
        else:
            return None

    def embed_doc(self, csv_data):
        contents: List[str] = []
        metadata: List[dict] = []

        reader = csv.DictReader(io.StringIO(csv_data))
        for row in reader:
            content = row.get('content', '')
            contents.append(content)
            metadata.append(row)

        # Load Data to vectorstore
        embedding = OpenAIEmbeddings()
        vectorstore = FAISS.from_texts(
            texts=contents, embedding=embedding, metadatas=metadata)

        # Make sure the directory exists before saving the vectorstore
        os.makedirs(os.path.dirname(self.vectorstore_path), exist_ok=True)

        # Serialize the FAISS index and save to a file
        with open(self.vectorstore_path, "wb") as f:
            serialized_faiss_bytes = vectorstore.serialize_to_bytes()
            f.write(serialized_faiss_bytes)

    def vector_search(self, query: str, number_of_outputs: int) -> str:
        print('User question: ' + query)
        print(os.getcwd())
        print(self.vectorstore_path)

        # Load the vectorstore using the new method
        vectorstore = self.load_vectorstore()

        if vectorstore is not None:
            print("Vectorstore loaded successfully")

            # Get the top X documents from the vectorstore
            docs_and_scores = vectorstore.similarity_search_with_score(
                query, number_of_outputs)
            # docs = vectorstore.similarity_search(query, number_of_outputs)

            context_for_LLM = ""
            docs_result = []
            for doc, score in docs_and_scores:
                doc_content = doc.metadata['content']
                # Remove content from metadata dict
                doc.metadata.pop('content', None)

                doc.metadata['score'] = float(score)

                doc_dict = {
                    'metadata': doc.metadata,
                    'content': doc_content
                }
                # print(doc_dict)
                docs_result.append(doc_dict)

            context_for_LLM = '\n\n'.join(
                doc['content'] for doc in docs_result)

            # print("context_for_LLM")
            # print('\n\n'.join(item for item in context_for_LLM))

            return docs_result, context_for_LLM
        else:
            print("vectorstore not found")
            return [], ""

    def searchByField(self, field: str, search_terms: List[str]):
        # Load the vectorstore
        vectorstore = self.load_vectorstore()
        if vectorstore is None:
            print("vectorstore not found")
            return []

        search_terms_str = ', '.join(search_terms)
        all_db = vectorstore.similarity_search(search_terms_str, k=500)

        docs_content = ""
        filtered_docs_result = []

        # if field and search_terms are not empty then filter vectorstore
        if field and search_terms_str:
            print(f"Searching {search_terms} in {field}")

            for row in all_db:
                # Filter rows where any term from the list [search_terms] is found in the specified field of row.metadata
                if any(re.search(r'{}'.format(term.lower()), row.metadata.get(field, '').lower()) for term in search_terms):
                    doc_content = row.metadata['content']
                    row.metadata.pop('content', None)

                    doc_dict = {
                        'metadata': row.metadata,
                        'content': doc_content
                    }
                    filtered_docs_result.append(doc_dict)

            context_for_LLM = '\n\n'.join(
                doc['content'] for doc in filtered_docs_result)

            print("context_for_LLM")
            print(context_for_LLM)

            return filtered_docs_result, context_for_LLM

        # If one of the argumets is empty then return semantically related items
        else:
            print(
                f"Searching {search_terms_str} by similarity in the embedded content")

            docs_and_scores = vectorstore.similarity_search_with_score(
                search_terms_str, k=20)

            for row, score in docs_and_scores:
                if score < 0.55:
                    doc_content = row.metadata['content']
                    row.metadata.pop('content', None)

                    doc_dict = {
                        'metadata': row.metadata,
                        'content': f"{doc_content}\n{field}: {row.metadata.get(field)}"
                    }
                    filtered_docs_result.append(doc_dict)

            context_for_LLM = [doc['content']
                               for doc in filtered_docs_result]
            print("context_for_LLM")
            print('\n\n'.join(item for item in context_for_LLM))

            return filtered_docs_result, context_for_LLM
