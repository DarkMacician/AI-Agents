import tweepy
import time
import schedule
from pymongo import MongoClient
from datetime import datetime, UTC, timedelta

# 🛠️ Twitter API Authentication
BEARER_TOKEN = "YOUR_BEARER_TOKEN"
client = tweepy.Client(bearer_token=BEARER_TOKEN)

# 🛠️ Connect to MongoDB
MONGO_URI = "YOUR_MONGO_URI"
mongo_client = MongoClient(MONGO_URI)
db = mongo_client["Twitter"]
tweets_collection = db["Tweets"]  # ✅ Existing tweets collection
replies_collection = db["Replies"]  # ✅ New collection for replies

# ✅ Ensure unique index for reply_id (Prevents duplicates)
replies_collection.create_index("reply_id", unique=True)

# 🛠️ Fetch tweet IDs from MongoDB
def get_saved_tweet_ids():
    """Retrieve all tweet IDs stored in MongoDB."""
    return [tweet["tweet_id"] for tweet in tweets_collection.find({}, {"tweet_id": 1})]

# 🛠️ Fetch replies for a given tweet
def fetch_replies(tweet_id):
    """Fetch all replies to a specific tweet using conversation_id."""
    query = f"conversation_id:{tweet_id} -is:retweet lang:en"
    start_time = (datetime.now(UTC) - timedelta(days=7)).isoformat()  # Last 7 days
    next_token = None
    all_replies = []

    while True:
        try:
            response = client.search_recent_tweets(
                query=query,
                tweet_fields=["created_at", "author_id", "conversation_id"],
                user_fields=["username"],
                expansions=["author_id"],
                start_time=start_time,
                max_results=100,
                next_token=next_token
            )

            if not response.data:
                break  # No more replies

            users = {user["id"]: user["username"] for user in response.includes["users"]} if response.includes else {}

            for reply in response.data:
                username = users.get(reply.author_id, "Unknown")

                reply_data = {
                    "reply_id": reply.id,
                    "tweet_id": tweet_id,  # ✅ Links to original tweet
                    "created_at": reply.created_at,
                    "post_owner": username,
                    "text": reply.text
                }

                all_replies.append(reply_data)

            next_token = response.meta.get("next_token")
            if not next_token:
                break  # No more pages

            time.sleep(1)  # ✅ Prevent rate limits

        except tweepy.errors.TooManyRequests as e:
            print("⚠️ Rate limit reached. Waiting before retrying...")
            time.sleep(60)
        except Exception as e:
            print(f"❌ Error fetching replies for {tweet_id}: {e}")
            break

    return all_replies

# 🛠️ Save replies to MongoDB (No Duplicates)
def save_replies():
    tweet_ids = get_saved_tweet_ids()

    for tweet_id in tweet_ids:
        print(f"🚀 Fetching replies for tweet {tweet_id}...")
        replies = fetch_replies(tweet_id)

        if not replies:
            print(f"🔹 No replies found for {tweet_id}")
            continue

        for reply in replies:
            if not replies_collection.find_one({"reply_id": reply["reply_id"]}):  # ✅ Check if reply exists
                try:
                    replies_collection.insert_one(reply)
                    print(f"✅ Saved reply {reply['reply_id']} for tweet {tweet_id}")
                except Exception as e:
                    print(f"❌ Error saving reply: {e}")
            else:
                print(f"🔄 Skipping duplicate reply {reply['reply_id']}")

# 🛠️ Schedule to run every 15 minutes
schedule.every(15).minutes.do(save_replies)

print("🚀 Starting reply fetcher... Running every 15 minutes!")

while True:
    schedule.run_pending()
    time.sleep(60)  # ✅ Check schedule every minute