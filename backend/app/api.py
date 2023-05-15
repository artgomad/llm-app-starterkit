from fastapi import FastAPI, WebSocket
from fastapi.middleware.cors import CORSMiddleware
import openai
from dotenv import load_dotenv
import os
import json
from app.chains.BasicChatChain import BasicChatChain
import asyncio

app = FastAPI()

load_dotenv()
openai.api_key = os.environ.get('OPENAI_API_KEY')

# Define which front-end origins are allowed to make requests
origins = [
    "https://project-zszmhke1xyd6rlfxgg1i.framercanvas.com",  # Framer Canvas
    "https://comprehensive-value-405432.framer.app"  # A framer publised website
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
        chatlog = json.loads(data)['chatlog']
        chatlog_strings = ""

        # Format chatlog to be fed as agent memory
        for item in chatlog:
            chatlog_strings += item['role'] + ': ' + item['content'] + '\n'

        chat_chain = BasicChatChain.create_chain()

        llm_response = chat_chain.run({'chat_history': chatlog_strings})

        print('llm response = ')
        print(llm_response)

        await websocket.send_json({
            "data":  llm_response,
        })
