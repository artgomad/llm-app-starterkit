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

        chatlog_strings = ""
        # Format chatlog to be fed as agent memory
        for item in chatlog:
            chatlog_strings += item['role'] + ': ' + item['content'] + '\n'

        chat_chain = BasicChatChain.create_chain()

        llm_response = chat_chain.run(
            {'system_message': system_message,
             'user_message_template': user_message_template,
             'chat_history': chatlog_strings})

        print('llm response = ')
        print(llm_response)

        await websocket.send_json({
            "data":  llm_response,
        })


class CSVData(BaseModel):
    item: str
    csv: str



@app.post("/create_vectorstore")
async def create_vectorstore(data: CSVData):
    item = json.loads(data.item)
    file_name = item['file_name']
    csv_data = data.csv

    print("INITIALISING VECTORSTORE CREATION")

    docsearch = Faiss.load_vectorstore(file_name)

    if docsearch is None:
        # Create the vectorstore
        docsearch = Faiss.embed_doc(file_name=file_name, csv_data=csv_data)
    else:
        print("VECTORSTORE ALREADY EXISTS")

    return {"data": "saved"}


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
