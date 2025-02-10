from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from transformers import AutoModelForCausalLM, AutoTokenizer
import torch

# Initialize the app
app = FastAPI()

# Configure CORS
origins = [
    "http://localhost:3000",
    "https://memetrade-co.fun",
    "https://www.memetrade-co.fun"
]

app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"]
)

# Load the CodeLlama model
local_model_path = "codellama/CodeLlama-7b"
print("Loading model...")
tokenizer = AutoTokenizer.from_pretrained(local_model_path)
model = AutoModelForCausalLM.from_pretrained(local_model_path, torch_dtype=torch.float16, device_map="auto")


# Define request and response schema
class CodePrompt(BaseModel):
    prompt: str
    max_tokens: int = 200


class CodeResponse(BaseModel):
    generated_code: str


# Endpoint for generating code
@app.post("/generate_code", response_model=CodeResponse)
async def generate_code(request: CodePrompt):
    try:
        # Tokenize and generate code
        inputs = tokenizer(request.prompt, return_tensors="pt").to("cuda")
        output = model.generate(**inputs, max_new_tokens=request.max_tokens)

        # Decode and return result
        generated_code = tokenizer.decode(output[0], skip_special_tokens=True)
        return {"generated_code": generated_code}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))