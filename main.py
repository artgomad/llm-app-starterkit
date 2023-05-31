import uvicorn
import os

if __name__ == "__main__":
    # Run on Heroku, the code below will make sure that your FastAPI application is listening on the correct port. Heroku dynamically assigns a port number to your application using the $PORT environment variable. You can access this variable in your Python code using os.environ.get('PORT').
    port = int(os.environ.get('PORT', 8000))
    uvicorn.run("app.api:app", host='0.0.0.0', port=port)
