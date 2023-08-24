from fastapi import FastAPI, WebSocket, UploadFile, File
from fastapi.middleware.cors import CORSMiddleware
from typing import Dict
import openai
from dotenv import load_dotenv
import traceback
import os
import json
import pickle
from pydantic import BaseModel
import asyncio
import signal
from app.chains.BasicChatChain import basicOpenAICompletion
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
    "https://script.googleusercontent.com",
    "https://aquamarine-copywriter-978461.framer.app/",
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
        await websocket.send_json({"message": "Let me think..."})

        # Process the received data from the client
        payload = json.loads(data)

        chatlog = payload['chatlog']
        knowledge_base = payload.get('knowledge_base')
        temperature = payload.get('temperature', 0)
        model_name = payload.get('model', 'gpt-3.5-turbo')
        context_items = payload.get('context_items', 3)
        functions = payload.get('functions', None)
        function_call = payload.get('function_call', "auto")

        chatlog_strings = ""
        context = ""
        all_product_info = []

        # Format chatlog to be fed as agent memory
        for item in chatlog:
            chatlog_strings += item['role'] + ': ' + item['content'] + '\n'

        user_question = chatlog[-1]['content']
        returned_context = "You haven't defined any knowledge base."

        # Retrieve context from vectorstore
        if knowledge_base is not None:
            # Use the last chatlog message as search query
            query = chatlog[-1]['content']  # chatlog_strings #
            faiss = Faiss(file_name=knowledge_base)
            docs, docs_content = faiss.vector_search(
                query=query, number_of_outputs=context_items)

            context = docs_content
            print('context = ')
            print(context)

            if context == "":
                print('No context found')
                returned_context = "The knowledge base you defined doesn't exit yet. Execute the code from your Google Sheets App Script extension"
            else:
                print('We found a context!')
                returned_context = context

        try:
            llm_response, inputPrompt = basicOpenAICompletion(
                temperature=temperature,
                model_name=model_name,
                chatlog=chatlog,
                chat_history=chatlog_strings,
                context="",  # context # Removed the context from basic answer
                user_question=user_question,
                functions=functions,
                function_call=function_call,)

            print('llm response = ')
            print(llm_response)

            function_call_output = llm_response['choices'][0]['message'].get(
                'function_call')
            print('function_call_output = ')
            print(function_call_output)

            if function_call_output is not None:
                await websocket.send_json({"message": "Searching our product database..."})
                # context_for_LLM = context
                print(function_call_output.arguments)
                context_for_LLM = function_call_output.arguments
                print('Calling a function!')

                # With this function I want to return the basic content of all products that match the search terms
                if function_call_output['name'] == 'search_food_products':
                    print(function_call_output['name'])
                    # Transform the arguments property from a string to JSON
                    arguments = json.loads(function_call_output['arguments'])
                    field = arguments.get('field', "")
                    search_terms = arguments.get('search_terms', [])

                    faiss = Faiss(file_name=knowledge_base)
                    all_product_info, context_for_LLM = faiss.searchByField(
                        field, search_terms)

                    # If the search fails we make sure to pass the context to the next LLM call
                    if not context_for_LLM:
                        context_for_LLM = context

                # With this function I want to return all the metadata of a single product
                elif function_call_output['name'] == 'read_product_details':
                    print(function_call_output['name'])
                    arguments = json.loads(function_call_output['arguments'])
                    product_name = arguments.get('product_name', "")

                    faiss = Faiss(file_name=knowledge_base)
                    all_product_info, context_for_LLM = faiss.vector_search(
                        query=product_name, number_of_outputs=1)

                    context_for_LLM = "\n\n".join(
                        f"Full product information: {json.dumps(doc['metadata'], indent=2)}"
                        for doc in all_product_info
                    )

                    print('All Product info = ')
                    print(context_for_LLM)
                else:
                    print('function without effect')

                await websocket.send_json({"message": "Products found, give me few seconds to answer you..."})
                # Make a new basicOpenAICompletion with the new database as context
                try:
                    llm_response, inputPrompt = basicOpenAICompletion(
                        temperature=temperature,
                        model_name=model_name,
                        chatlog=chatlog,
                        chat_history=chatlog_strings,
                        context=context_for_LLM,
                        user_question=user_question,
                        functions=functions,
                        function_call='none',)

                    print('llm response after function call = ')
                    print(llm_response)

                    # update the context to be returned to the client
                    returned_context = context_for_LLM if context_for_LLM else "No context found from the function call."

                except Exception as e:
                    traceback.print_exc()
                    print(
                        "Error occurred when executing basicOpenAICompletion after the function call.")

            await websocket.send_json({
                "data":  llm_response,
                "context":  returned_context,
                "context_metadata": all_product_info,
                "inputPrompt": inputPrompt,
                "function_used": function_call_output,
            })

        except Exception as e:
            traceback.print_exc()
            error_message = str(e)
            tb_str = traceback.format_exc()
            tb_lines = tb_str.split('\n')
            last_5_lines_tb = '\n'.join(tb_lines[-6:])
            print("ERROR: ", last_5_lines_tb)
            await websocket.send_json({
                "error": error_message,
                "error_traceback": last_5_lines_tb,
                "context":  returned_context,
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
    docs, docs_content = faiss.vector_search(
        query=query, number_of_outputs=number_of_outputs)
    context = json.dumps(docs, sort_keys=True, indent=4)

    # Send a response back to the client
    await websocket.send_json({"data": context})


@app.websocket("/ws-audio")
async def websocket_endpoint_audio(websocket: WebSocket):
    await websocket.accept()

    while True:
        # Receive the binary audio data
        audio_data = await websocket.receive_bytes()
        # Process the received data from the client
        if audio_data:
            temporary_dir = os.path.abspath('data/temporary_files')

            with open(os.path.join(temporary_dir, "audio.webm"), "wb") as f:
                f.write(audio_data)
                print("Saved audio file to audio.webm")

            audio_file = open(os.path.join(temporary_dir, "audio.webm"), "rb")
            transcript = openai.Audio.transcribe("whisper-1", audio_file)

            # Save first transcript localy
            with open(os.path.join(temporary_dir, "transcript.txt"), "w") as f:
                f.write(transcript.text)
                print(f"{transcript.text} saved")

            await websocket.send_json({"data": transcript.text})

        else:
            print("Received invalid payload")


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
