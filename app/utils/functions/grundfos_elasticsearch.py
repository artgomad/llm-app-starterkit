import requests
import json


def grundfos_elasticsearch(graphql_query):
    print("Triggered grundfos_elasticsearch")
    print("GraphQL Query:", graphql_query)
    # The endpoint URL from the schema
    url = "https://api.grundfos.com/search"

    # API Key for the security, you need to replace 'your_api_key_here' with your actual API key
    headers = {
        "Content-Type": "application/json",
    }

    payload = {
        "query": graphql_query
    }
    try:
        response = requests.post(url, headers=headers,
                                 data=json.dumps(payload))

        # Checking if the request was successful
        if response.status_code == 200:
            # Do something with the response, for example, print the text of the response
            # print(response.text)
            return response.json()
        else:
            # Handle request errors
            print(f"Request failed with status code: {response.status_code}")
            print(f"Response Body: {response.text}")
            return None

    except requests.exceptions.RequestException as e:
        # Catch any exceptions that requests might throw
        print(f"An error occurred: {e}")
        return None
