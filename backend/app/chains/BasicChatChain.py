from langchain.schema import HumanMessage, SystemMessage
from langchain.prompts import BaseChatPromptTemplate
from langchain.chat_models import ChatOpenAI
from langchain import LLMChain

from dotenv import load_dotenv
from fastapi import WebSocket
from typing import List


load_dotenv()

RED = "\033[1;31m"
GREEN = "\033[0;32m"
BLUE = "\033[34m"
YELLOW = "\033[1;33m"
RESET = "\033[0m"

system_message = """You are Ben, a digital assistant from ING.
Ben is designed to be able to assist with a wide range of tasks, from answering simple questions to providing in-depth explanations on topics related to ING. 
"""

first_message_template = """

**Previous conversation history:
{chat_history}

Begin!
"""


class CustomPromptTemplate(BaseChatPromptTemplate):
    template: str

    def format_messages(self, **kwargs) -> str:
        kwargs["chat_history"] = kwargs.get("chat_history", "")

        formatted = self.template.format(**kwargs)

        llm_prompt_input = [SystemMessage(
            content=system_message), HumanMessage(content=formatted)]

        print('FORMATED PROMPT AS RECEIVED BY THE LLM\n')
        print(llm_prompt_input)

        return llm_prompt_input


class BasicChatChain():
    def create_chain():
        prompt = CustomPromptTemplate(
            template=first_message_template,
            input_variables=["chat_history"],
        )

        llm = ChatOpenAI(temperature=0, model_name='gpt-3.5-turbo')

    # Declare a chain that will trigger an openAI completion with the given prompt
        llm_chain = LLMChain(
            llm=llm,
            prompt=prompt,
        )

        return llm_chain
