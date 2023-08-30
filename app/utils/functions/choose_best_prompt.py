import asyncio
import json
import traceback
from app.chains.BasicChatChain import basicOpenAICompletion


async def choose_best_prompt(websocket, prompt_options, chatlog, chat_history, user_question):
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

    # We are going to inject a new system prompt for this first opperation
    system_prompt = {
        "role": "system",
                "content": "Always call one of the provided functions"
    }

    for i, item in enumerate(chatlog):
        if item["prompt"]["role"] == "system":
            chatlog[i] = system_prompt
            break

    try:
        # LLM call to choose the best system prompt
        llm_response, inputPrompt = basicOpenAICompletion(
            temperature=0,
            model_name="gpt-3.5-turbo-0613",
            chatlog=chatlog,
            chat_history=chat_history,
            context="",  # Routing decision is not based on database context
            user_question=user_question,
            functions=prompt_choosing_function,
        )

        function_call_output = llm_response['choices'][0]['message'].get(
            'function_call')

        chosen_prompt_name = json.loads(
            function_call_output['name'])

        new_system_prompt = prompt_options[chosen_prompt_name]

        print('chosen_prompt = ')
        print(new_system_prompt)

        # Send the profile update to the client
        await websocket.send_json({
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
            "context":  "Error when updating the customer profile.",
        })

        return None
