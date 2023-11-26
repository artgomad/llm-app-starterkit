import requests
import json


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
            output_str = json.dumps(response.json())

            metadata = response.json()['data']['search']['items']
            print(
                f"{bcolors.OKGREEN}Output received!{bcolors.ENDC}")
            return output_str, metadata

        else:
            # Handle request errors
            print(f"Request failed with status code: {response.status_code}")
            print(f"Response Body: {response.text}")
            return None, None

    except requests.exceptions.RequestException as e:
        # Catch any exceptions that requests might throw
        print(f"An error occurred: {e}")
        return None, None
