from dotenv import load_dotenv
from openai import OpenAI
from fastapi import WebSocket
import time

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

    async def get_assistant_and_thread(self, assistant_id=None, thread_id=None):
        # Perform async operations here to initialize assistant and thread
        if assistant_id:
            self.assistant = self.get_assistant(assistant_id)
        else:
            self.assistant = await self.create_assistant(self.name, self.description, self.instructions, self.tools, self.model)

        if thread_id:
            self.thread = self.get_thread(thread_id)
        else:
            self.thread = await self.start_new_thread()

        return self

    async def create_assistant(self, name, description, instructions, tools, model):
        """
        Create a new assistant with the given parameters.
        """
        assistant = await self.client.beta.assistants.create(
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

    async def start_new_thread(self):
        """
        Start a new chat with a user.
        """
        empty_thread = await self.client.beta.threads.create()
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

    async def add_message(self, thread, content):
        """
        Add a message to a chat/Thread.
        """
        thread_message = await self.client.beta.threads.messages.create(
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

    async def get_answer(self, thread, assistant=None):
        """
        Run the thread with the assistant.
        """
        if not assistant:
            assistant = self.assistant
        run = await self.client.beta.threads.runs.create(
            thread_id=thread.id,
            assistant_id=assistant.id,
        )
        # wait for the run to complete
        while True:
            runInfo = await self.client.beta.threads.runs.retrieve(thread_id=thread.id, run_id=run.id)
            if runInfo.completed_at:
                # elapsed = runInfo.completed_at - runInfo.created_at
                # elapsed = time.strftime("%H:%M:%S", time.gmtime(elapsed))
                print(f"Run completed")
                break
            print("Waiting 1sec...")
            time.sleep(1)

        print("All done...")
        # Get messages from the thread
        messages = await self.client.beta.threads.messages.list(thread.id)
        message_content = messages.data[0].content[0].text.value
        return message_content
