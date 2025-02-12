import tweepy
import torch
import numpy as np
import time
from datetime import datetime, timedelta, UTC
from scipy.special import softmax
from pymongo import MongoClient
from transformers import AutoModelForSequenceClassification, AutoTokenizer, AutoConfig

# 🛠️ Twitter API Authentication
BEARER_TOKEN = "AAAAAAAAAAAAAAAAAAAAAFBbzAEAAAAAgcvj0fJRFZWu3qnyCA5pgEH%2Bj18%3DcB2Ut7ir5zB08zCDSiwAhzHiW1Pk4FWycy51YErjuCo27McPu6"
client = tweepy.Client(bearer_token=BEARER_TOKEN)

# 🛠️ Connect to MongoDB
MONGO_URI = "mongodb+srv://hoaiduy:introdatabase2024@cluster0.kvp0p.mongodb.net/?retryWrites=true&w=majority&appName=Cluster0"
mongo_client = MongoClient(MONGO_URI)
db = mongo_client["Twitter"]
collection = db["Tweets"]

# ✅ Efficient indexing to delete old tweets and prevent duplicates
collection.create_index("created_at", expireAfterSeconds=2592000)  # Delete after 30 days
collection.create_index("tweet_id", unique=True)

# 🛠️ Keywords & Sentiment Model
CRYPTO_KEYWORDS = ["BTC", "ETH", "SNS", "ADA", "SOL"]
LABELS = {
    "BTC": "Bitcoin",
    "ETH": "Ethereum",
    "SNS": "Sui Name Service",
    "ADA": "Cardano",
    "SOL": "Solana",
}

# Load Sentiment Model
MODEL_PATH = "sentiment_model"
tokenizer = AutoTokenizer.from_pretrained(MODEL_PATH)
config = AutoConfig.from_pretrained(MODEL_PATH)
model = AutoModelForSequenceClassification.from_pretrained(MODEL_PATH)

# 🛠️ Preprocess text function
def preprocess(text):
    new_text = []
    for t in text.split(" "):
        t = '@user' if t.startswith('@') else t
        t = 'http' if t.startswith('http') else t
        new_text.append(t)
    return " ".join(new_text)

# 🛠️ Sentiment Analysis
def analyze_sentiment(text):
    text = preprocess(text)
    encoded_input = tokenizer(text, return_tensors='pt')
    with torch.no_grad():
        output = model(**encoded_input)
    scores = softmax(output[0][0].numpy())
    sentiment_label = config.id2label[np.argmax(scores)]
    confidence = np.round(float(np.max(scores)), 4)
    return sentiment_label, confidence

# 🛠️ Extract crypto mentions
def extract_currencies(text):
    return [symbol for symbol in CRYPTO_KEYWORDS if symbol in text.upper()]

# 🛠️ Fetch tweets
def fetch_tweets():
    query = "(BTC OR ETH OR SNS OR ADA OR SOL) -is:retweet lang:en"
    start_time = (datetime.now(UTC) - timedelta(minutes=16)).isoformat()

    try:
        response = client.search_recent_tweets(
            query=query,
            tweet_fields=["created_at", "id", "author_id"],
            expansions=["author_id"],
            max_results=100
        )
        return response
    except tweepy.errors.TooManyRequests as e:
        reset_time = int(e.response.headers.get("x-rate-limit-reset", time.time() + 60))
        wait_time = max(reset_time - time.time(), 60)
        print(f"⚠️ Rate limit reached. Retrying in {wait_time:.2f} seconds...")
        time.sleep(wait_time)
        return None
    except Exception as e:
        print(f"❌ Error fetching tweets: {e}")
        return None

# 🛠️ Main loop
while True:
    print("🚀 Fetching new tweets...")
    response = fetch_tweets()

    if response is None or not response.data:
        print("⚠️ No new tweets found. Sleeping for 15 min...")
        time.sleep(900)
        continue

    author_dict = {user.id: user.username for user in response.includes["users"]}

    for tweet in response.data:
        if collection.find_one({"tweet_id": tweet.id}):  # Skip duplicates
            print(f"🔄 Skipping duplicate tweet: {tweet.id}")
            continue

        author = author_dict.get(tweet.author_id, "Unknown")
        link = f"https://twitter.com/{author}/status/{tweet.id}"
        currencies = extract_currencies(tweet.text)
        labels = [LABELS[c] for c in currencies]
        sentiment, confidence = analyze_sentiment(tweet.text)

        tweet_data = {
            "tweet_id": tweet.id,
            "created_at": tweet.created_at,
            "author": author,
            "link": link,
            "text": tweet.text,
            "currencies": currencies,
            "labels": labels,
            "sentiment": sentiment,
            "confidence": confidence
        }

        try:
            collection.insert_one(tweet_data)
            print(f"✅ Saved: {tweet.id} | {author} | Sentiment: {sentiment} ({confidence})")
        except Exception as e:
            print(f"❌ Error saving tweet {tweet.id}: {e}")

    print("🎯 Waiting 15 minutes before next fetch...")
    time.sleep(900)