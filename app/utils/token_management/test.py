import requests

# Define the URL of the API server
url = "https://llm-app-starterkit.herokuapp.com/googleSheetsAPI"

# Define the request payload according to the schema
payload = {
    "spreadsheet_id": "1ljoRDB7EAOEzD-agCkVPiJU8-JU6oRRu2sd5UN4M3ic",
    "sheet_name": "User profile",
    "inputJSON": {
        "products_selected": [5],
        "six_month_discount": "Yes"
    }
}

# Set the headers to indicate JSON content
headers = {
    "Content-Type": "application/json"
}

# Make the POST request
response = requests.post(url, json=payload, headers=headers)

# Check the response status code
if response.status_code == 200:
    # Successful response
    result = response.json()
    print("Calculation Result:", result)
else:
    # Error occurred
    print("Error:", response.status_code, response.text)
