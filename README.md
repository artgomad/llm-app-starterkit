# Developing LLM APIs with FastAPI

## Want to use this project?

1. Fork/Clone

2. Rename .env-template file as .env and enter your personal API key from https://platform.openai.com/account/api-keys

3. Run the server-side FastAPI app locally from the terminal window:

   ```sh
   $ cd backend
   $ python3.X -m venv env (only the first time, use the python version you have installed)
   $ source env/bin/activate
   (env)$ pip install -r requirements.txt (only when requirements change)
   (env)$ python main.py

   To stop the process and make changes to the backend
   Open new terminal window
   $ lsof -i :8000 (to see the current processes that are running)
   $ kill {PID} (example: $ kill 25355 , will kill the current active process, and allow you to restart the backend with $ python main.py)
   ```


