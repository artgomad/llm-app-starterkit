import asyncio
import json
import traceback
from app.chains.BasicChatChain import basicOpenAICompletion


async def update_customer_profile(client, websocket, model_name, chatlog, chat_history, user_question, functions):
    if functions is None:
        return None

    try:
        llm_response, inputPrompt = basicOpenAICompletion(
            client=client,
            temperature=0,
            model_name=model_name,
            chatlog=chatlog,
            chat_history=chat_history,
            context="",  # No need for external context to update customer profile
            user_question=user_question,
            functions=functions,
            function_call={"name": "update_profile"})

        function_call_output = llm_response['choices'][0]['message'].get(
            'function_call')

        customer_profile_update = json.loads(
            function_call_output['arguments'])

        print('customer_profile_update = ')
        print(customer_profile_update)

        # Send the profile update to the client
        await websocket.send_json({
            "customer_profile_update": customer_profile_update,
        })

        return customer_profile_update

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
