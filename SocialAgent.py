import os
import openai
import time
import json
import re
from pymongo import MongoClient
from fastapi import FastAPI, Query
from pydantic import BaseModel
from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()
# Initialize FastAPI
app = FastAPI()

client = MongoClient("mongodb+srv://prompt:123@cluster0.admu7.mongodb.net/")
db = client["MemeTradeCO"]

# Cryptocurrency collections
crypto_collections = {
    "BTC": db["BTCUSDT"],
    "ETH": db["ETHUSDT"],
    "BNB": db["BNBUSDT"],
    "ADA": db["ADAUSDT"],
    "SOL": db["SOLUSDT"]
}

# MongoDB Connection
crypto_list = {
    "Bitcoin": "BTC", "BTC": "BTC",
    "Ethereum": "ETH", "ETH": "ETH",
    "Binance Coin": "BNB", "BNB": "BNB",
    "Cardano": "ADA", "ADA": "ADA",
    "Solana": "SOL", "SOL": "SOL"
}

# Detect cryptocurrency symbols in the prompt
def detect_cryptos(prompt):
    found_cryptos = {crypto_list[key] for key in crypto_list if re.search(rf"\b{re.escape(key)}\b", prompt, re.IGNORECASE)}
    return list(found_cryptos)

# Fetch last 5 records for detected cryptos
def fetch_last_records(cryptos):
    data = {}
    for symbol in cryptos:
        collection = crypto_collections.get(symbol+"USDT")
        if collection:
            last_records = list(collection.find({}, {"_id": 0}).sort([("_id", -1)]).limit(5))
            data[symbol] = last_records
    return json.dumps(data, indent=4, default=str)

# OpenAI API Key
openai.api_key = os.getenv("OPENAI_API_KEY")

# Detect cryptocurrency names in the prompt
def detect_cryptos(prompt):
    return [crypto for crypto in crypto_list if re.search(rf"\b{re.escape(crypto)}\b", prompt, re.IGNORECASE)]

# ChatGPT-4 interaction
def chat_with_gpt4(prompt):
    retries = 3
    wait_time = 1
    for attempt in range(retries):
        try:
            response = openai.ChatCompletion.create(
                model="gpt-4",
                messages=[{"role": "user", "content": prompt}],
                max_tokens=500,
                temperature=0.7,
                top_p=1.0,
                frequency_penalty=0,
                presence_penalty=0
            )

            output_text = response['choices'][0]['message']['content'].strip()
            if ("real-time".lower() in output_text.lower()
                    or "As an AI".lower() in output_text.lower()
                    or "Sorry".lower() in output_text.lower()):
                new_prompt = prompt + "\n\nAdditional Market Data:\n" + fetch_last_records(detect_cryptos(output_text))
                return chat_with_gpt4(new_prompt)

            return output_text
        except openai.error.RateLimitError:
            time.sleep(wait_time)
            wait_time *= 2
        except Exception as e:
            print(f"Error: {e}")
            return None
    return None

# Image generation using DALL·E
def generate_image(prompt):
    try:
        found_cryptos = detect_cryptos(prompt)
        image_prompt = found_cryptos if found_cryptos else prompt
        new_prompt = ""
        for i in image_prompt:
            new_prompt += " and " + i
        print(f"Generating image for: {new_prompt}")

        response = openai.Image.create(
            model="dall-e-3",
            prompt=new_prompt,
            n=1,
            size="1024x1024"
        )
        return response["data"][0]["url"]
    except Exception as e:
        print(f"Image generation error: {e}")
        return None

# Request Body Schema
class GeneratePostRequest(BaseModel):
    prompt: str
    image: bool = False

# Generate post endpoint
@app.post("/generate_post")
def generate_post(request: GeneratePostRequest):
    text = chat_with_gpt4(request.prompt)
    if request.image:
        image_url = generate_image(request.prompt)
        return {"text": text, "image_url": image_url}
    return {"text": text}

# Regenerate text endpoint
@app.post("/regenerate_text")
def regenerate_text(prompt: str = Query(..., description="Enter the prompt to regenerate text")):
    text = chat_with_gpt4(prompt)
    return {"text": text}

# Regenerate image endpoint
@app.post("/regenerate_image")
def regenerate_image(prompt: str = Query(..., description="Enter the prompt to regenerate image")):
    image_url = generate_image(prompt)
    return {"image_url": image_url}