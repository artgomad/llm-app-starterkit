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
from app.utils.functions.search_products_based_on_profile import search_products_based_on_profile
from app.utils.functions.read_product_details import read_product_details
from app.utils.functions.compare_products import compare_products
from app.utils.functions.update_customer_profile import update_customer_profile
from app.utils.functions.choose_best_prompt import choose_best_prompt
from app.utils.functions.google_sheets_calculator import google_sheets_calculator


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

        # 00 EXTRACT ALL API PARAMETERS
        payload = json.loads(data)
        chatlog = payload['chatlog']
        prompt_options = payload.get('dynamic_system_prompt')
        knowledge_base = payload.get('knowledge_base')
        temperature = payload.get('temperature', 0)
        model_name = payload.get('model', 'gpt-3.5-turbo')
        model_for_profiling = payload.get('model_profiling', 'gpt-3.5-turbo')
        context_items = payload.get('context_items', 3)
        functions = payload.get('functions', None)
        update_profile_function = payload.get('update_profile_function', None)
        function_call = payload.get('function_call', "auto")
        score_threshold = payload.get('score_threshold', 0.5)

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
            # print('context = ')
            # print(context)

            if context == "":
                print('No context found')
                returned_context = "The knowledge base you defined doesn't exit yet. Execute the code from your Google Sheets App Script extension"
            else:
                print('We found a context!')
                returned_context = context

        # 01 EXECUTE CUSTOMER PROFILE UPDATE AND CHOSING SYSTEM PROMPT IN PARALLEL
        customer_profile_update, new_system_prompt = await asyncio.gather(
            update_customer_profile(
                websocket=websocket,
                model_name=model_for_profiling,
                chatlog=chatlog,
                chat_history=chatlog_strings,
                user_question=user_question,
                functions=update_profile_function,
            ),
            choose_best_prompt(
                websocket=websocket,
                prompt_options=prompt_options,
                chatlog=chatlog,
                chat_history=chatlog_strings,
                user_question=user_question,

            )
        )

        if new_system_prompt is not None:
            # Replace the system prompt of the chatlog with the one selected for the next operation
            for i, item in enumerate(chatlog):
                if item["role"] == "system":
                    chatlog[i] = new_system_prompt
                    break

        # 02 CORE GPT FUNCTION ROUTER
        try:
            llm_response, inputPrompt = basicOpenAICompletion(
                temperature=temperature,
                model_name=model_name,
                chatlog=chatlog,
                chat_history=chatlog_strings,
                context="",  # Routing decision is not based on database context
                user_question=user_question,
                functions=functions,
                function_call=function_call,)

            print('llm response = ')
            print(llm_response)

            function_call_output = llm_response['choices'][0]['message'].get(
                'function_call')

            # 03 EXECUTE THE FUNCTION CHOSEN BY GPT
            if function_call_output is not None:
                await websocket.send_json({"message": "Searching our database..."})
                print('Calling a function!')
                print(function_call_output['name'])
                print(function_call_output)

                context_for_LLM = context
                function_output = json.loads(function_call_output['arguments'])

                # This function returns the basic content of all products that match the search terms
                if function_call_output['name'] == 'compare_products':
                    all_product_info, context_for_LLM = compare_products(
                        function_output, knowledge_base, context)

                # This function returns all the metadata of a single product given the product name
                elif function_call_output['name'] == 'read_product_details':
                    all_product_info, context_for_LLM = read_product_details(
                        function_output, knowledge_base)

                # This function returns all products that match the customer profile under a certain threshold
                elif function_call_output['name'] == 'search_products_based_on_profile':
                    all_product_info, context_for_LLM = search_products_based_on_profile(
                        customer_profile_update, knowledge_base, score_threshold)

                # This function is a simple semantic search on all the database
                elif function_call_output['name'] == 'semantic_search_all_db':
                    context_for_LLM = context  # Retrieved from the original semantic search
                    all_product_info = docs  # Retrieved from the original semantic search

                 # This function is a simple semantic search on all the database
                elif function_call_output['name'] == 'calculate':
                    google_sheets_calculator()
                    context_for_LLM = context  # Retrieved from the original semantic search
                    all_product_info = docs  # Retrieved from the original semantic search

                else:
                    print('function without effect')
                    # context_for_LLM equals a function_call_output stringified
                    context_for_LLM = json.dumps(
                        function_call_output['arguments'])

                # Send a message to the client to let them know the function executed correctly
                await websocket.send_json({"message": "Products found, give me few seconds to answer you..."})

                # 04 GPT ANSWER INFORMED BY THE FUNCTION CALL OUTPUT
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
