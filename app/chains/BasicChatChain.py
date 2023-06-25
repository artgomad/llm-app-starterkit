from langchain.schema import HumanMessage, SystemMessage, AIMessage
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


#first_message_template = "**Previous conversation history:{chat_history}"


class CustomPromptTemplate(BaseChatPromptTemplate):
    def format_messages(self, **kwargs) -> str:
            chatlog = kwargs.get("chatlog", [])

            kwargs["chat_history"] = kwargs.get("chat_history", "")
            kwargs["context"] = kwargs.get("context", "")
            kwargs["user_question"] = kwargs.get("user_question", "")

            system_message_template = kwargs.get("system_message", "")
            system_message = system_message_template.format(**kwargs)
            
            messages = []
            for item in chatlog:
                 if item['role'] == 'user':
                     # if this is the last message from chatlog
                     if item == chatlog[-1]:
                         user_message_template = kwargs.get("user_message_template", "")
                         user_message = user_message_template.format(**kwargs)
                         messages.append(HumanMessage(content=user_message)) 
                     else:
                         messages.append(HumanMessage(content=item['content']))

                 elif item['role'] == 'system':
                    messages.append(SystemMessage(content=system_message)) 

                 else:
                     messages.append(AIMessage(content=item['content']))   

            print('FORMATED PROMPT AS RECEIVED BY THE LLM\n')
            print(messages)
            return messages


class BasicChatChain():
    def create_chain(temperature, model_name):
        prompt = CustomPromptTemplate(
            input_variables=["chat_history",
                             "system_message", "chatlog", "user_message_template", "context", "user_question"],
        )

        llm = ChatOpenAI(temperature=temperature, model_name=model_name)

            # Declare a chain that will trigger an openAI completion with the given prompt
        llm_chain = LLMChain(
                llm=llm,
                prompt=prompt,
            )


        return llm_chain
