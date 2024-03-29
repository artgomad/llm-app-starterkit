import asyncio
import json
import traceback
from app.chains.BasicChatChain import basicOpenAICompletion


async def choose_best_prompt(client, websocket, prompt_options, customer_profile, chatlog, chat_history, user_question):
    if prompt_options is None:
        return None

    prompt_choosing_function = [
        {
            "name": item["name"],
            "description": item["description"],
            "parameters": {
                "type": "object",
                        "properties": {
                            "dummy_property": {
                                "type": "null",
                            }, }

            },
        } for item in prompt_options]

    prompts_array = [
        item['prompt']
        for item in prompt_options]

    # We are going to inject a new system prompt for this first opperation
    system_prompt = {
        "role": "system",
        "content":
        f"""You are a classification algorithm whose goal is to select the most relevant function given the customer profile below and the previous conversation.
            You are not a chatbot, NEVER answer the user directly. ALWAYS select one of the given functions.
            CUSTOMER PROFILE:
            {customer_profile}""",
    }

    for i, item in enumerate(chatlog):
        if item["role"] == "system":
            chatlog[i] = system_prompt
            break

    try:
        # LLM call to choose the best system prompt
        llm_response, inputPrompt = basicOpenAICompletion(
            client=client,
            temperature=0,
            model_name="gpt-3.5-turbo-0613",
            chatlog=chatlog,
            chat_history=chat_history,
            context="",  # Routing decision is not based on database context
            user_question=user_question,
            functions=prompt_choosing_function,
            function_call="auto",
        )

        print("llm_response")
        print(llm_response)

        function_call_output = llm_response.choices[0].message.function_call

        print("function_call_output")
        print(function_call_output)

        new_system_prompt = None
        chosen_prompt_name = ""

        if function_call_output:
            chosen_prompt_name = function_call_output.name

            for item in prompt_options:
                if item['name'] == chosen_prompt_name:
                    new_system_prompt = item['prompt']
                    break
        else:
            chosen_prompt_name = prompt_options[0]['name']
            new_system_prompt = prompts_array[0]

        print('chosen_prompt = ')
        print(new_system_prompt)

        # Send the profile update to the client
        await websocket.send_json({
            "intent": chosen_prompt_name,
            "selected_system_prompt": new_system_prompt,
        })

        return new_system_prompt

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
            "context":  "Error when GPT was choosing it's system prompt.",
        })

        return None
