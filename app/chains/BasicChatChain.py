import openai
from dotenv import load_dotenv

load_dotenv()
    
def format_messages(chatlog=[], chat_history="", context="", user_question=""):
    messages = []
    for item in chatlog:
        if item['role'] == 'user':
            user_message = item['content'].format(chat_history=chat_history, context=context, user_question=user_question)
            messages.append({"role": "user", "content": user_message})

        elif item['role'] == 'system':
            system_message = item['content'].format(chat_history=chat_history, context=context, user_question=user_question)
            messages.append({"role": "system", "content": system_message})
        
        elif item['role'] == 'assistant':
            messages.append({"role": "assistant", "content": item['content']})

        elif item['role'] == 'function':
            messages.append({"role": "function", "content": item['content']})

    print('FORMATED PROMPT AS RECEIVED BY THE LLM\n')
    print(messages)
    return messages


def basicOpenAICompletion(temperature, model_name, chatlog, chat_history, context, user_question, functions):
    messages = format_messages(chatlog, chat_history, context, user_question)
    response = openai.ChatCompletion.create(
        model=model_name,
        messages=messages,
        temperature=temperature,
        functions=functions,
    )
    
    return response, messages
