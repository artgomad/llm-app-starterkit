from dotenv import load_dotenv
from openai import OpenAI
from fastapi import WebSocket
import time
import json
from app.utils.functions.grundfos_elasticsearch import grundfos_elasticsearch

load_dotenv()  # Load .env file


class bcolors:
    HEADER = '\033[95m'
    OKBLUE = '\033[94m'
    OKCYAN = '\033[96m'
    OKGREEN = '\033[92m'
    WARNING = '\033[93m'
    FAIL = '\033[91m'
    ENDC = '\033[0m'
    BOLD = '\033[1m'
    UNDERLINE = '\033[4m'


class GPT_Assistant_API:
    """
    A class to interact with an AI assistant API, allowing the creation of assistants,
    retrieval of existing ones, starting new chats, adding messages to chats, and running
    chat threads with an assistant.
    """

    def __init__(self, client, name, description, instructions, tools=[], model="gpt-3.5-turbo-1106"):
        self.client = client
        self.name = name
        self.description = description
        self.instructions = instructions
        self.tools = tools
        self.model = model

    def get_assistant_and_thread(self, assistant_id=None, thread_id=None):
        # Perform async operations here to initialize assistant and thread
        if assistant_id:
            assistant = self.get_assistant(assistant_id)
        else:
            assistant = self.create_assistant(
                self.name, self.description, self.instructions, self.tools, self.model)

        if thread_id:
            thread = self.get_thread(thread_id)
        else:
            thread = self.start_new_thread()

        return assistant, thread

    def create_assistant(self, name, description, instructions, tools, model):
        """
        Create a new assistant with the given parameters.
        """
        assistant = self.client.beta.assistants.create(
            name=name,
            description=description,
            instructions=instructions,
            tools=tools,
            model=model
        )
        print("Created assistant with id:",
              f"{bcolors.HEADER}{assistant.id}{bcolors.ENDC}")
        return assistant

    def get_assistant(self, assistant_id):
        """
        Get an already made assistant by ID.
        """
        assistant = self.client.beta.assistants.retrieve(assistant_id)
        print("Retrieved assistant with id:",
              f"{bcolors.HEADER}{assistant.id}{bcolors.ENDC}")
        return assistant

    def start_new_thread(self):
        """
        Start a new chat with a user.
        """
        empty_thread = self.client.beta.threads.create()
        print("Created thread with id:",
              f"{bcolors.HEADER}{empty_thread.id}{bcolors.ENDC}")
        return empty_thread

    def get_thread(self, thread_id):
        """
        Retrieve previous chat/Thread by ID.
        """
        thread = self.client.beta.threads.retrieve(thread_id)
        print("Reusing thread with id:",
              f"{bcolors.HEADER}{thread.id}{bcolors.ENDC}")
        return thread

    def add_message(self, thread, content):
        """
        Add a message to a chat/Thread.
        """
        thread_message = self.client.beta.threads.messages.create(
            thread_id=thread.id,
            role="user",
            content=content,
        )
        return thread_message

    def get_messages_in_chat(self, thread):
        """
        Get the previous messages in a chat/Thread.
        """
        messages = self.client.beta.threads.messages.list(thread_id=thread.id)
        return messages

    def get_answer(self, thread, assistant=None):
        """
        Run the thread with the assistant.
        """
        if not assistant:
            assistant = self.assistant
        run = self.client.beta.threads.runs.create(
            thread_id=thread.id,
            assistant_id=assistant.id,
        )
        start_time = time.time()

        # wait for the run to complete
        while True:
            current_time = time.time()
            elapsed_time = current_time - start_time

            runInfo = self.client.beta.threads.runs.retrieve(
                thread_id=thread.id, run_id=run.id)
            print("Run status: ", runInfo.status)

            run_steps = self.client.beta.threads.runs.steps.list(
                thread_id=thread.id, run_id=run.id)
            # print(run_steps)

            if run_steps.data:
                if run_steps.data[0].step_details.tool_calls:
                    function_tool_call = run_steps.data[0].step_details.tool_calls[0]
                    # print(function_tool_call)

                    function_arguments = function_tool_call.function.arguments
                    function_name = function_tool_call.function.name

                    # Print out the variables
                    print(
                        f"{bcolors.OKCYAN}Function Arguments: {function_arguments}{bcolors.ENDC}")
                    print(
                        f"{bcolors.OKCYAN}Function Name: {function_name}{bcolors.ENDC}")

                    if function_name and function_arguments:
                        # Parse the JSON string into a dictionary
                        arguments_dict = json.loads(function_arguments)
                        # Call the function using its name as a string and passing the arguments
                        output = getattr(globals()[function_name], function_name)(
                            **arguments_dict)

                        print(output)

            if runInfo.completed_at:
                print(f"Run completed")
                break
            elif elapsed_time > 10:  # Check if more than 10 seconds have elapsed
                print("Timeout: The run did not complete in 10 seconds.")
                break

            print("Waiting 1sec...")
            time.sleep(1)

        print("All done...")
        # Get messages from the thread
        messages = self.client.beta.threads.messages.list(thread.id)
        # print(messages.data[0])

        message_content = messages.data[0].content[0].text.value

        message_object = {
            'role': messages.data[0].role,
            'content': message_content,
            'metadata': []
        }

        # print(message_object)
        print(f"{bcolors.OKGREEN}{message_content}{bcolors.ENDC}")

        return message_object
