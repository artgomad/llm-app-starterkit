# Developing LLM APIs with FastAPI

## Want to use this project?

1. Fork/Clone

2. Rename .env-template file as .env and enter your personal API key from https://platform.openai.com/account/api-keys

3. Run the server-side FastAPI app locally from the terminal window:

   ```sh
   $ cd backend
   $ python --version
   $ python3.X -m venv env (only the first time, use the python version you have installed)
   $ source env/bin/activate
   (env)$ pip install -r requirements.txt (only when requirements change)
   (env)$ python main.py

   To stop the process and make changes to the backend
   Open new terminal window
   $ lsof -i :8000 (to see the current processes that are running)
   $ kill {PID} (example: $ kill 25355 , will kill the current active process, and allow you to restart the backend with $ python main.py)
   ```

4. Work with a Framer front end (see example here https://satisfaction-hurt-939139.framer.app/)

5. Debug Heroku
   ```sh
   $ heroku login
   $ heroku logs --tail --app llm-app-starterkit
   ```

## Google Sheets Access Tokens

A recurring problem with Heroku applications that connect to Google Sheets API is the expiration of the
access credentials and tokens to Google Sheets API.
To fix this error, follow this steps:

1.  Run app/utils/token_mamagement/flow_to_obtain_googlesheets_tokens.py to update client_secret.json and toke.json in the root directory
2.  Copy it's content into the corresponding Heroku Config Vars (GOOGLE_CLIENT_SECRET and GOOGLE_SHEETS_TOKENS) in the Heroku dashboard.
3.  Save the updated vars and the Google Sheets connection should work again!
