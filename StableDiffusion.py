from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from io import BytesIO
import torch
from diffusers import StableDiffusionPipeline
import base64
from PIL import Image

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

# Load the Stable Diffusion model
model_id = "sd-legacy/stable-diffusion-v1-5"
print("Loading model...")
pipe = StableDiffusionPipeline.from_pretrained(
    model_id,
    torch_dtype=torch.float16
)
pipe.to("cuda")  # Move the model to GPU

# Define request and response schema
class TextPrompt(BaseModel):
    prompt: str

class ImageResponse(BaseModel):
    base64_image: str

# Endpoint for generating an image
@app.post("/generate_image", response_model=ImageResponse)
async def generate_image(prompt: TextPrompt):
    try:
        # Generate the image
        image = pipe(prompt.prompt).images[0]

        # Convert the image to a base64 string
        buffer = BytesIO()
        image.save(buffer, format="PNG")
        buffer.seek(0)
        image_base64 = base64.b64encode(buffer.getvalue()).decode("utf-8")

        return {"base64_image": image_base64}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))