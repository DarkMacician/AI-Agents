import os

from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
import openai
from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()
# Initialize FastAPI app
app = FastAPI()

# Set OpenAI API key (Ensure to set your key in an environment variable for security)
openai.api_key = os.getenv("OPENAI_API_KEY")

# Request model
class ChatRequest(BaseModel):
    message: str
    model: str = "gpt-4o"  # Default model


# Chatbot endpoint
@app.post("/chat")
async def chat(request: ChatRequest):
    if not openai.api_key:
        raise HTTPException(status_code=500, detail="OpenAI API key is missing.")

    try:
        response = openai.ChatCompletion.create(
            model=request.model,
            messages=[{"role": "user", "content": request.message}]
        )
        return {"response": response["choices"][0]["message"]["content"]}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))