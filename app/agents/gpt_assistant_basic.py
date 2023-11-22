from dotenv import load_dotenv
from openai import OpenAI
from fastapi import WebSocket

load_dotenv()  # Load .env file
client = OpenAI()


class GPT_Assistant_API:
    """
    A class to interact with an AI assistant API, allowing the creation of assistants,
    retrieval of existing ones, starting new chats, adding messages to chats, and running
    chat threads with an assistant.
    """

    def __init__(self, client, name, description, instructions, tools=[], model="gpt-3.5-turbo-1106"):
        """
        Create a new Assistant.
        """
        self.client = client
        self.assistant = self.create_assistant(
            name, description, instructions, tools, model)

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
        return assistant

    def get_assistant(self, assistant_id):
        """
        Get an already made assistant by ID.
        """
        assistant = self.client.beta.assistants.retrieve(assistant_id)
        return assistant

    def start_new_chat(self):
        """
        Start a new chat with a user.
        """
        empty_thread = self.client.beta.threads.create()
        return empty_thread

    def get_chat(self, thread_id):
        """
        Retrieve previous chat/Thread by ID.
        """
        thread = self.client.beta.threads.retrieve(thread_id)
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

    def run_chat(self, thread, assistant=None):
        """
        Run the thread with the assistant.
        """
        if not assistant:
            assistant = self.assistant
        run = self.client.beta.threads.runs.create(
            thread_id=thread.id,
            assistant_id=assistant.id,
        )
        return run


async def assistant_api_interaction(websocket, assistant_id, thread_id, name, description, instructions, tools, model, content):
    # Instantiate the assistant API class
    api = GPT_Assistant_API(client, name, description,
                            instructions, tools, model)

    # Create or retrieve an assistant based on assistant_id
    assistant = api.get_assistant(
        assistant_id) if assistant_id else api.assistant

    # Retrieve or start a new chat based on thread_id
    thread = api.get_chat(thread_id) if thread_id else api.start_new_chat()

    # Add the message to the thread and run the chat
    api.add_message(thread, content)
    response = api.run_chat(thread, assistant)

    # Run the thread with the assistant with the new message
    response = await api.run_chat(thread, assistant)
    await websocket.send_json({"message": "Processing..."})

    # Retrieve the latest message from the chat history
    history = await api.get_messages_in_chat(thread)
    last_message = history.data[-1] if history.data else None

    # Send the latest message to the front-end
    if last_message:
        await websocket.send_json({
            "role": last_message.role,
            "content": last_message.content[0].text.value,
            "thread_id": thread.id
        })
