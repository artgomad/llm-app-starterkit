from fastapi import FastAPI, WebSocket, UploadFile, File
from fastapi.middleware.cors import CORSMiddleware
from typing import Dict
import openai
from dotenv import load_dotenv
import os
import json
import pickle
from pydantic import BaseModel
import asyncio
import signal
from app.chains.BasicChatChain import BasicChatChain
from app.utils.vectorstores.Faiss import Faiss


load_dotenv()

app = FastAPI()
exit_flag = False
openai.api_key = os.environ.get('OPENAI_API_KEY')

# Define which front-end origins are allowed to make requests
origins = [
    "https://project-zszmhke1xyd6rlfxgg1i.framercanvas.com",  # Framer Canvas
    "https://comprehensive-value-405432.framer.app",  # A framer publised website
    "https://script.google.com",
    "https://script.googleusercontent.com"
]

app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"]
)

class CSVData(BaseModel):
    item: str
    csv: str

@app.websocket("/ws")
async def websocket_endpoint(websocket: WebSocket):
    await websocket.accept()

    while True:
        data = await websocket.receive_text()

        # Process the received data from the client
        payload = json.loads(data)

        chatlog = payload['chatlog']
        system_message = payload['system_message']
        user_message_template = payload['user_message_template']
        knowledge_base = payload.get('knowledge_base')

        chatlog_strings = ""
        context = ""
   
        # Format chatlog to be fed as agent memory
        for item in chatlog:
            chatlog_strings += item['role'] + ': ' + item['content'] + '\n'

        user_question = chatlog[-1]['content']
        returned_context = "You haven't defined any knowledge base."

         # Retrieve context from vectorstore
        if knowledge_base is not None:
            # Use the last 5 chatlog items as search query
            query = chatlog[-1]['content'] #chatlog_strings #
            faiss = Faiss(file_name=knowledge_base)
            docs, docs_content = faiss.vector_search(query= query, number_of_outputs=3)

            context = json.dumps(docs_content)

            if docs is not []:
                returned_context = "The knowledge base you defined doesn't exit yet. Execute the code from your Google Sheets App Script extension"
            else:
                returned_context = context
                
        try:
            chat_chain, error = BasicChatChain.create_chain()

            if chat_chain is None:
                # if chat_chain is None, there was an error creating the chain
                error_message = "Error creating chat chain: " + str(error)
                await websocket.send_json({
                    "error": error_message
                })
                continue  # jump to the next iteration of the loop

            llm_response = chat_chain.run(
            {'system_message': system_message,
             'user_message_template': user_message_template,
             'chat_history': chatlog_strings,
             'context': context,
             'user_question': user_question})

            print('llm response = ')
            print(llm_response)

            await websocket.send_json({
                "data":  llm_response,
                "context":  returned_context,
            })
        except Exception as e:
            # Handle specific exceptions here
            error_message = str(e) + ": " + error
            await websocket.send_json({
                "error": error_message
            })

       


@app.post("/create_vectorstore")
async def create_vectorstore(data: CSVData):
    item = json.loads(data.item)
    file_name = item['file_name']
    csv_data = data.csv

    print("INITIALISING VECTORSTORE CREATION")

    faiss = Faiss(file_name=file_name)

    # Directly create a new vectorstore, replacing the old one if it exists
    faiss.embed_doc(csv_data=csv_data)

    return {"data": "VECTORSTORE CREATED"}

@app.websocket("/search-database")
async def websocket_endpoint_search_database(websocket: WebSocket):

    await websocket.accept()

    # Receive the JSON payload
    payload_str = await websocket.receive_text()
    payload = json.loads(payload_str)

    query = payload['query']
    knowledge_base = payload['knowledge_base']
    number_of_outputs = payload['number_of_outputs']

    print("query = ", query)

    faiss = Faiss(file_name=knowledge_base)

    # Directly create a new vectorstore, replacing the old one if it exists
    docs, docs_content = faiss.vector_search(query=query, number_of_outputs=number_of_outputs)
    context = json.dumps(docs, sort_keys=True, indent=4)

    # Send a response back to the client
    await websocket.send_json({"data": context})


# Register a signal handler for SIGINT (Ctrl-C)
def handle_exit_signal(signum, frame):
    global exit_flag
    exit_flag = True

@app.on_event("startup")
def startup_event():
    # Start a task to check the exit flag periodically
    asyncio.create_task(check_exit_flag())

async def check_exit_flag():
    while not exit_flag:
        await asyncio.sleep(0.1)  # Adjust the sleep duration as needed

    # Perform any cleanup tasks or additional shutdown logic here
    print("Exiting gracefully...")
    # Optionally, you can close any open connections or perform cleanup tasks

    # Stop the application server
    await app.stop()

# Attach the signal handler to the SIGINT signal
signal.signal(signal.SIGINT, handle_exit_signal)
