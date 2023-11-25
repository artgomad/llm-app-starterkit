import requests
import json


def grundfos_elasticsearch(query):
    print("Triggered grundfos_elasticsearch")
    print(query)
    # The endpoint URL from the schema
    url = "https://api.grundfos.com/search"

    # API Key for the security, you need to replace 'your_api_key_here' with your actual API key
    headers = {
        "Content-Type": "application/json",
    }

    # Making the POST request
    response = requests.post(url, headers=headers,
                             data=json.dumps(query))

    # Checking if the request was successful
    if response.status_code == 200:
        # Do something with the response, for example, print the text of the response
        print(response.text)
        return response.text
    else:
        # Handle request errors
        print(f"Request failed with status code: {response.status_code}")
        return None
