from fastapi import FastAPI, WebSocket, UploadFile, File, HTTPException, Request
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
from app.utils.functions.google_sheets_calculator_v2 import google_sheets_calculator_v2, Config
from app.agents.gpt_assistant_basic import GPT_Assistant_API
from app.utils.functions.dalle_3 import generate_image


load_dotenv()

app = FastAPI()
exit_flag = False
openai.api_key = os.environ.get('OPENAI_API_KEY')
client = openai.OpenAI()

# Define which front-end origins are allowed to make requests
origins = [
    "https://project-zszmhke1xyd6rlfxgg1i.framercanvas.com",  # Framer Canvas
    "https://comprehensive-value-405432.framer.app",  # A framer publised website
    "https://script.google.com",
    "https://script.googleusercontent.com",
    "https://aquamarine-copywriter-978461.framer.app/",
    # Sanofi project
    "https://framer.com/projects/Diabetes-Management-Chatbot--LjcZAHtH8keu6MDl96ea-b41wd?preview=1&node=zjX5sW56V",
    "https://modest-products-919721.framer.app",
    "https://diabetes-management-sanofi.framer.ai",
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
        customer_profile = payload.get('customer_profile', None)
        stringified_customer_profile = json.dumps(
            customer_profile, indent=2) if customer_profile else ""
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
            print(knowledge_base)
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
                client=client,
                websocket=websocket,
                model_name=model_for_profiling,
                chatlog=chatlog,
                chat_history=chatlog_strings,
                user_question=user_question,
                functions=update_profile_function,
            ),
            choose_best_prompt(
                client=client,
                websocket=websocket,
                prompt_options=prompt_options,
                customer_profile=stringified_customer_profile,
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
                client=client,
                temperature=temperature,
                model_name=model_name,
                chatlog=chatlog,
                customer_profile=stringified_customer_profile,
                chat_history=chatlog_strings,
                context=context,  # "" if Routing decision is not based on database context
                user_question=user_question,
                functions=functions,
                function_call=function_call,)

            print('llm response = ')
            print(llm_response)

            function_call_output = llm_response.choices[0].message.function_call

            # 03 EXECUTE THE FUNCTION CHOSEN BY GPT
            if function_call_output is not None:
                await websocket.send_json({"message": "Searching our database..."})
                print('Calling a function!')
                print(function_call_output.name)
                print(function_call_output)

                context_for_LLM = context
                function_output = json.loads(function_call_output.arguments)

                # This function returns the basic content of all products that match the search terms
                if function_call_output.name == 'compare_products':
                    all_product_info, context_for_LLM = compare_products(
                        function_output, knowledge_base, context)

                # This function returns all the metadata of a single product given the product name
                elif function_call_output.name == 'read_product_details':
                    all_product_info, context_for_LLM = read_product_details(
                        function_output, knowledge_base)

                # This function returns all products that match the customer profile under a certain threshold
                elif function_call_output.name == 'search_products_based_on_profile':
                    all_product_info, context_for_LLM = search_products_based_on_profile(
                        customer_profile_update, knowledge_base, score_threshold)

                # This function is a simple semantic search on all the database
                elif function_call_output.name == 'semantic_search_all_db':
                    context_for_LLM = context  # Retrieved from the original semantic search
                    all_product_info = docs  # Retrieved from the original semantic search

                 # This function makes calculations with Google sheets:
                elif function_call_output.name.startswith('calculate'):
                    all_product_info, context_for_LLM = google_sheets_calculator(
                        function_output)

                else:
                    print('function without effect')
                    # context_for_LLM equals a function_call_output stringified
                    context_for_LLM = json.dumps(
                        function_call_output.arguments)

                # Send a message to the client to let them know the function executed correctly
                await websocket.send_json({"message": "Products found, give me few seconds to answer you..."})

                # 04 GPT ANSWER INFORMED BY THE FUNCTION CALL OUTPUT
                try:
                    llm_response, inputPrompt = basicOpenAICompletion(
                        client=client,
                        temperature=temperature,
                        model_name=model_name,
                        chatlog=chatlog,
                        customer_profile=stringified_customer_profile,
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
                "data":  llm_response.dict(),
                "context":  returned_context,
                "context_metadata": all_product_info,
                "inputPrompt": inputPrompt,
                "function_used": function_call_output.dict(),
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


@app.websocket("/assistantAPI")
async def assistantAPI(websocket: WebSocket):
    await websocket.accept()

    while True:
        data = await websocket.receive_text()
        await websocket.send_json({"message": "Let me think..."})

        # 00 EXTRACT ALL API PARAMETERS
        payload = json.loads(data)
        # assistant and thread id need to be passed from the front-end to maintain the connection to the same assistant
        assistant_id_to_use = payload.get('assistant_id_to_use', None)
        thread_id_to_use = payload.get('thread_id_to_use', None)
        name = payload.get('name', 'Default Assistant')
        description = payload.get('description', '')
        instructions = payload.get('instructions', '')
        tools = payload.get('tools', [])
        model = payload.get('model', "gpt-3.5-turbo-1106")
        content = payload.get('content', '')

        try:
            api = GPT_Assistant_API(
                client, websocket, name, description, instructions, tools, model)
            assistant, thread = api.get_assistant_and_thread(
                assistant_id_to_use, thread_id_to_use)

            api.add_message(thread, content)

            # Call the synchronous get_answer method within an executor
            # This maintains the synchronous nature required by the OpenAI SDK
            # while still being able to communicate asynchronously over WebSockets
            loop = asyncio.get_running_loop()
            response = await loop.run_in_executor(None, api.get_answer, thread, assistant)

            await websocket.send_json({
                "data":  response,
                "assistant_id": assistant.id,
                "thread_id": thread.id
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
            })


@app.websocket("/dalle3")
async def dalle3(websocket: WebSocket):
    await websocket.accept()

    while True:
        data = await websocket.receive_text()
        await websocket.send_json({"message": "Request recieved..."})

        # 00 EXTRACT ALL API PARAMETERS
        payload = json.loads(data)

        image_description = payload.get('image_description', None)
        size = payload.get('size', "1024x1024")

        try:
            image_url, images_list = generate_image(
                prompt=image_description, n=1, size=size)

            await websocket.send_json({
                "generated_image":  image_url,
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
            })


@app.websocket("/completion_with_streaming")
async def completion_with_streaming(websocket: WebSocket):
    await websocket.accept()

    while True:
        data = await websocket.receive_text()
        await websocket.send_json({"message": "Let me think..."})

        # 00 EXTRACT ALL API PARAMETERS
        payload = json.loads(data)

        chatlog = payload.get('chatlog', None)
        model = payload.get('model', None)
        temperature = payload.get('temperature', None)

        try:
            stream = client.chat.completions.create(
                model=model,
                messages=chatlog,
                temperature=temperature,
                stream=True,
            )

            for chunk in stream:
                if chunk.choices[0].delta.content is not None:
                    await websocket.send_json({
                        "chunk":  chunk.choices[0].delta.content,
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
            })


class SpreadsheetInput(BaseModel):
    spreadsheet_id: str
    sheet_name: str
    inputJSON: dict


@app.post("/googleSheetsAPI")
async def google_sheets_api_endpoint(input: SpreadsheetInput):
    try:
        spreadsheet_id = input.spreadsheet_id or '1ljoRDB7EAOEzD-agCkVPiJU8-JU6oRRu2sd5UN4M3ic'
        sheet_name = input.sheet_name or 'User profile'
        inputJSON = input.inputJSON

        config = Config()

        objects, message = google_sheets_calculator_v2(
            config, spreadsheet_id, sheet_name, inputJSON)

        print(objects, message)

        return {
            "data": message,
            "context_metadata": objects,
        }

    except Exception as e:
        traceback.print_exc()
        error_message = str(e)
        tb_str = traceback.format_exc()
        tb_lines = tb_str.split('\n')
        last_5_lines_tb = '\n'.join(tb_lines[-6:])
        print("ERROR: ", last_5_lines_tb)
        raise HTTPException(status_code=500, detail={
            "error": error_message,
            "error_traceback": last_5_lines_tb,
        })


@app.websocket("/rag_&_SPR")
async def websocket_endpoint(websocket: WebSocket):
    await websocket.accept()

    while True:
        data = await websocket.receive_text()
        await websocket.send_json({"message": "Let me think..."})

        # 00 EXTRACT ALL API PARAMETERS
        payload = json.loads(data)
        chatlog = payload['chatlog']
        knowledge_base = payload.get('knowledge_base')
        temperature = payload.get('temperature', 0)
        model_name = payload.get('model', 'gpt-3.5-turbo')
        context_items = payload.get('context_items', 3)
        functions = payload.get('functions', None)
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
            print(knowledge_base)
            query = chatlog[-1]['content']  # chatlog_strings #
            faiss = Faiss(file_name=knowledge_base)
            docs, docs_content = faiss.vector_search(
                query=query, number_of_outputs=context_items)

            # Initialize lists to store content and metadata SPR values
            contents = []
            spr_values = []
            sources = []

            # Loop through each document in docs_result
            for doc in docs:
                contents.append(doc['content'])
                sources.append(doc['metadata']['doc_name'] +
                               ' - ' + doc['metadata']['h1'])

                # Check if SPR is unique before adding to spr_values
                spr = doc['metadata']['SPR']
                if spr not in spr_values:
                    spr_values.append(spr)

            # Convert lists to formatted strings
            contents_str = '\n'.join(contents)
            spr_values_str = '\n'.join(spr_values)

            for item in chatlog:
                if (item['role'] == 'system'):
                    context = item['content'].replace(
                        "{context}", contents_str).replace("{customer_profile}", spr_values_str)
                    print(context)

            if context == "":
                print('No context found')
                returned_context = "The knowledge base you defined doesn't exit yet. Execute the code from your Google Sheets App Script extension"
            else:
                print('We found a context!')
                returned_context = context

        # LLM COMPLETION
        try:
            llm_response, inputPrompt = basicOpenAICompletion(
                client=client,
                temperature=temperature,
                model_name=model_name,
                chatlog=chatlog,
                # I'm passing the spr as second variable to ingest in the prompt
                customer_profile=spr_values_str,
                chat_history=chatlog_strings,
                context=contents_str,  # I'm passing the contents as context
                user_question=user_question,
                functions=functions,
                function_call='none',)

            print('llm response = ')
            print(llm_response)

            await websocket.send_json({
                "data":  llm_response.dict(),
                "context":  returned_context,
                "context_metadata": docs,
                "sources": sources,
                "inputPrompt": inputPrompt,
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
